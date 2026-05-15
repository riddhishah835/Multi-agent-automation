"""
src/agents/runtime.py
──────────────────────
Phase 2: Agent Execution Engine

This module is the "muscles" layer. It:
  1. Instantiates the three compliance agents (the_reader, the_judge, the_scribe).
  2. Runs each agent against a given task, using only the tools returned by the pruner.
  3. Returns a typed AgentResult that P1 (Orchestrator) stores in Postgres.

Agent roles
-----------
  the_reader  → Extracts structured evidence from raw OCR output → List[EvidenceCard]
  the_judge   → Adversarially scans evidence for non-compliance  → List[Finding]
  the_scribe  → Drafts a professional consulting report           → Markdown string

Each agent is backed by the Google Gemini API (gemini-2.0-flash).
Tool calls are routed through mcp_bridge.call_tool() so every invocation
is captured in the audit trail.

Environment variables expected:
  GEMINI_API_KEY
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

import os
import google.generativeai as genai  # pip install google-generativeai

from src.agents.schemas import AgentResult, AuditState, EvidenceCard, Finding
from src.tools.mcp_bridge import call_tool
from src.tools.pruner import prune_for_agent
from src.tools.registry import ToolMeta

log = logging.getLogger(__name__)

# ── Gemini client (module-level singleton) ────────────────────────────────────

_model: genai.GenerativeModel | None = None


def _get_client() -> genai.GenerativeModel:
    global _model
    if _model is None:
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        _model = genai.GenerativeModel(
            model_name=MODEL,
            generation_config=genai.GenerationConfig(
                max_output_tokens=MAX_TOKENS,
                temperature=0.2,       # low temp = deterministic, good for audits
            ),
        )
    return _model


MODEL = "gemini-2.0-flash"
MAX_TOKENS = 4096


# ═════════════════════════════════════════════════════════════════════════════
# Public API — called by P1 Orchestrator
# ═════════════════════════════════════════════════════════════════════════════

def run_reader(state: AuditState, raw_ocr_output: Dict[str, Any]) -> AgentResult:
    """
    DAG Node A/B → C hand-off: Run the_reader agent.

    Parameters
    ----------
    state           : Current AuditState (provides tenant_id, source_file_hash, etc.)
    raw_ocr_output  : Output from mcp_bridge call_tool("ocr_unstructured" | "ocr_textract")

    Returns
    -------
    AgentResult whose .evidence_cards() gives a List[EvidenceCard].
    """
    task = (
        f"Extract all compliance-relevant evidence from the vendor document "
        f"'{state.vendor_name}' for tenant '{state.tenant_id}'. "
        f"Focus on: security controls, data privacy, availability SLAs, "
        f"financial risk indicators, KYC/AML signals."
    )
    return _run_agent(
        agent_role="reader",
        task=task,
        tenant_id=state.tenant_id,
        context={
            "ocr_output": raw_ocr_output,
            "source_file_hash": state.source_file_hash,
            "vendor_name": state.vendor_name,
        },
        system_prompt=_READER_SYSTEM,
        output_parser=_parse_reader_output,
    )


def run_judge(
    state: AuditState,
    evidence_cards: List[EvidenceCard],
    category: str,
) -> AgentResult:
    """
    DAG Node C: Run the_judge agent for a single compliance category.

    The Orchestrator calls this in parallel for each category
    (security, privacy, availability, financial, kyc, aml).

    Parameters
    ----------
    state           : Current AuditState.
    evidence_cards  : Output from run_reader().evidence_cards().
    category        : Compliance category to audit (e.g. "security").

    Returns
    -------
    AgentResult whose .findings() gives a List[Finding].
    """
    task = (
        f"Perform an adversarial compliance audit of '{state.vendor_name}' "
        f"for the '{category}' category. Find every reason to REJECT this vendor. "
        f"Do NOT look for compliance — look for non-compliance."
    )
    return _run_agent(
        agent_role="judge",
        task=task,
        tenant_id=state.tenant_id,
        context={
            "evidence_cards": [e.model_dump() for e in evidence_cards],
            "category": category,
            "vendor_name": state.vendor_name,
            "audit_id": state.audit_id,
        },
        system_prompt=_JUDGE_SYSTEM,
        output_parser=_parse_judge_output,
    )


def run_scribe(state: AuditState, findings: List[Finding]) -> AgentResult:
    """
    DAG Node E: Run the_scribe agent to produce the final Markdown report.

    Parameters
    ----------
    state    : Current AuditState (provides vendor_name, tenant_id, audit_id).
    findings : Consolidated findings from all run_judge() calls (post gap-analysis).

    Returns
    -------
    AgentResult whose .report_markdown() gives the full report string.
    """
    task = (
        f"Write a premium, consultant-grade compliance audit report for "
        f"'{state.vendor_name}' based on the provided findings. "
        f"Professional tone. Include an executive summary, risk matrix, "
        f"and actionable recommendations."
    )
    return _run_agent(
        agent_role="scribe",
        task=task,
        tenant_id=state.tenant_id,
        context={
            "findings": [f.model_dump() for f in findings],
            "vendor_name": state.vendor_name,
            "audit_id": state.audit_id,
            "tenant_id": state.tenant_id,
        },
        system_prompt=_SCRIBE_SYSTEM,
        output_parser=_parse_scribe_output,
    )


# ═════════════════════════════════════════════════════════════════════════════
# Internal execution engine
# ═════════════════════════════════════════════════════════════════════════════

def _run_agent(
    agent_role: str,
    task: str,
    tenant_id: str,
    context: Dict[str, Any],
    system_prompt: str,
    output_parser,
    max_tool_rounds: int = 5,
) -> AgentResult:
    """
    Core agentic loop:
      1. Prune tools for this role + task.
      2. Call Gemini with system prompt + context + available tools.
      3. If Gemini requests a tool, dispatch via mcp_bridge and feed result back.
      4. Repeat until Gemini returns a final text response (no more tool calls).
      5. Parse the final text into a typed output and wrap in AgentResult.
    """
    start_ms = time.time()
    tools_used: List[str] = []

    # Step 1 — prune tools
    available_tools = prune_for_agent(agent_role, task, tenant_id)
    tool_declarations = [_to_gemini_tool_declaration(t) for t in available_tools]

    # Step 2 — build conversation history
    user_message = _build_user_message(task, context)

    # Gemini uses a chat session for multi-turn tool calls
    model = _get_client()

    # Rebuild model with system instruction + tools for this specific agent call
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    agent_model = genai.GenerativeModel(
        model_name=MODEL,
        system_instruction=system_prompt,
        tools=tool_declarations if tool_declarations else None,
        generation_config=genai.GenerationConfig(
            max_output_tokens=MAX_TOKENS,
            temperature=0.2,
        ),
    )
    chat = agent_model.start_chat()
    final_text: str = ""

    try:
        for round_num in range(max_tool_rounds + 1):
            log.info(
                "runtime[%s]: API call round=%d tools_available=%d",
                agent_role, round_num, len(tool_declarations),
            )

            if round_num == 0:
                response = chat.send_message(user_message)
            # (subsequent rounds are handled inside the tool loop below)

            # Extract text parts
            text_parts = [
                part.text
                for candidate in response.candidates
                for part in candidate.content.parts
                if hasattr(part, "text") and part.text
            ]
            if text_parts:
                final_text = "\n".join(text_parts)

            # Check for tool calls
            tool_call_parts = [
                part
                for candidate in response.candidates
                for part in candidate.content.parts
                if hasattr(part, "function_call") and part.function_call.name
            ]

            if not tool_call_parts:
                log.info("runtime[%s]: agent finished (no tool calls)", agent_role)
                break

            if round_num == max_tool_rounds:
                log.warning("runtime[%s]: hit max_tool_rounds=%d", agent_role, max_tool_rounds)
                break

            # Step 3 — execute tool calls and feed results back
            tool_responses = []
            for part in tool_call_parts:
                fc = part.function_call
                tool_name = fc.name
                tool_input = dict(fc.args)
                tools_used.append(tool_name)

                log.info("runtime[%s]: tool_call name=%r", agent_role, tool_name)
                try:
                    result = call_tool(tool_name, tool_input)
                    tool_responses.append(
                        genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name=tool_name,
                                response={"result": json.dumps(result, default=str)},
                            )
                        )
                    )
                except Exception as exc:
                    log.error("runtime[%s]: tool %r failed: %s", agent_role, tool_name, exc)
                    tool_responses.append(
                        genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name=tool_name,
                                response={"error": str(exc)},
                            )
                        )
                    )

            # Send all tool results back in one turn
            response = chat.send_message(tool_responses)

        # Step 5 — parse output
        output = output_parser(final_text)
        duration_ms = (time.time() - start_ms) * 1000

        return AgentResult(
            agent_name=f"the_{agent_role}",
            status="success",
            output=output,
            tools_used=list(dict.fromkeys(tools_used)),
            duration_ms=round(duration_ms, 2),
        )

    except Exception as exc:
        log.exception("runtime[%s]: unhandled exception", agent_role)
        duration_ms = (time.time() - start_ms) * 1000
        return AgentResult(
            agent_name=f"the_{agent_role}",
            status="failed",
            output={},
            tools_used=tools_used,
            error=str(exc),
            duration_ms=round(duration_ms, 2),
        )


# ═════════════════════════════════════════════════════════════════════════════
# Output parsers
# ═════════════════════════════════════════════════════════════════════════════

def _parse_reader_output(raw_text: str) -> Dict[str, Any]:
    """
    Expects the_reader to return a JSON object with key 'evidence_cards'.
    Falls back gracefully if the model returns plain text.
    """
    try:
        cleaned = _strip_json_fences(raw_text)
        data = json.loads(cleaned)
        cards_raw = data.get("evidence_cards", [])
        # Validate each card against the schema
        validated = []
        for c in cards_raw:
            try:
                validated.append(EvidenceCard(**c).model_dump())
            except Exception as e:
                log.warning("reader: invalid EvidenceCard skipped: %s", e)
        return {"evidence_cards": validated, "raw_response": raw_text}
    except json.JSONDecodeError:
        log.warning("reader: response was not JSON — wrapping as raw text")
        return {"evidence_cards": [], "raw_response": raw_text}


def _parse_judge_output(raw_text: str) -> Dict[str, Any]:
    """
    Expects the_judge to return a JSON object with key 'findings'.
    Auto-assigns finding_id (UUID) if missing.
    """
    try:
        cleaned = _strip_json_fences(raw_text)
        data = json.loads(cleaned)
        findings_raw = data.get("findings", [])
        validated = []
        for f in findings_raw:
            f.setdefault("finding_id", str(uuid.uuid4()))
            f.setdefault("evidence", [])
            try:
                validated.append(Finding(**f).model_dump())
            except Exception as e:
                log.warning("judge: invalid Finding skipped: %s", e)
        return {"findings": validated, "raw_response": raw_text}
    except json.JSONDecodeError:
        log.warning("judge: response was not JSON — wrapping as raw text")
        return {"findings": [], "raw_response": raw_text}


def _parse_scribe_output(raw_text: str) -> Dict[str, Any]:
    """
    The scribe returns Markdown directly (no JSON wrapping needed).
    We store it under 'report_markdown'.
    """
    return {"report_markdown": raw_text.strip()}


# ═════════════════════════════════════════════════════════════════════════════
# Tool schema conversion
# ═════════════════════════════════════════════════════════════════════════════

def _to_gemini_tool_declaration(tool: ToolMeta) -> genai.protos.Tool:
    """
    Convert a ToolMeta (from registry.py) into a Gemini FunctionDeclaration tool.
    """
    properties = {}
    for param_name, param_type in tool.input_schema.items():
        # Map simple string type hints to Gemini's TYPE enum
        type_map = {
            "string": genai.protos.Type.STRING,
            "str":    genai.protos.Type.STRING,
            "int":    genai.protos.Type.INTEGER,
            "integer":genai.protos.Type.INTEGER,
            "float":  genai.protos.Type.NUMBER,
            "bool":   genai.protos.Type.BOOLEAN,
            "boolean":genai.protos.Type.BOOLEAN,
        }
        gemini_type = type_map.get(param_type.lower(), genai.protos.Type.STRING)
        properties[param_name] = genai.protos.Schema(type=gemini_type)

    fn = genai.protos.FunctionDeclaration(
        name=tool.name,
        description=tool.description,
        parameters=genai.protos.Schema(
            type=genai.protos.Type.OBJECT,
            properties=properties,
            required=list(tool.input_schema.keys()),
        ),
    )
    return genai.protos.Tool(function_declarations=[fn])


# ═════════════════════════════════════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════════════════════════════════════

def _build_user_message(task: str, context: Dict[str, Any]) -> str:
    """Serialise the task + context into a single user message string."""
    context_json = json.dumps(context, indent=2, default=str)
    return (
        f"TASK:\n{task}\n\n"
        f"CONTEXT (JSON):\n```json\n{context_json}\n```\n\n"
        f"Respond ONLY with the required JSON output. No preamble, no explanation."
    )


def _strip_json_fences(text: str) -> str:
    """Remove ```json ... ``` fences so json.loads() can parse the payload."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Drop first line (```json or ```) and last line (```)
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    return text.strip()


# ═════════════════════════════════════════════════════════════════════════════
# System prompts
# ═════════════════════════════════════════════════════════════════════════════

_READER_SYSTEM = """
You are the_reader, a specialist compliance evidence extractor.

Your ONLY job is to read the raw OCR output provided in CONTEXT and extract
every fact that is relevant to: security controls, data privacy, availability SLAs,
financial risk, KYC, and AML compliance.

Output rules (STRICT):
- Respond with ONLY a JSON object. No preamble. No markdown prose.
- Schema:
  {
    "evidence_cards": [
      {
        "quote":            "<verbatim text from document>",
        "page_number":      <integer>,
        "source_hash":      "<SHA-256 from context>",
        "source_filename":  "<filename from context>",
        "category":         "<security|privacy|availability|financial|kyc|aml>",
        "relevance_score":  <float 0.0–1.0>
      }
    ]
  }
- Include ONLY evidence with relevance_score >= 0.6.
- Prefer exact verbatim quotes; never paraphrase.
- Set relevance_score to 1.0 for critical controls, 0.8 for notable findings,
  0.6 for weak signals.
""".strip()

_JUDGE_SYSTEM = """
You are the_judge, an adversarial compliance auditor.

Your ONLY job is to find REASONS TO REJECT the vendor. Do NOT look for
compliance — look for non-compliance, gaps, ambiguities, and risks.

You are auditing a single compliance category provided in CONTEXT.

Output rules (STRICT):
- Respond with ONLY a JSON object. No preamble. No markdown prose.
- Schema:
  {
    "findings": [
      {
        "finding_id":             "<UUID string>",
        "category":               "<compliance category>",
        "severity":               "<critical|high|medium|low|info>",
        "title":                  "<short description, max 10 words>",
        "detail":                 "<full adversarial reasoning, 2-4 sentences>",
        "evidence":               [<subset of EvidenceCard objects from context>],
        "mitigation_suggestion":  "<one sentence suggestion>"
      }
    ]
  }
- Only raise findings that are directly supported by at least one evidence_card.
- Severity guide: critical = data breach risk or regulatory violation,
  high = significant control gap, medium = weak control, low = best-practice gap.
- Do NOT fabricate quotes. Use only quotes present in the evidence_cards.
""".strip()

_SCRIBE_SYSTEM = """
You are the_scribe, a senior consultant report writer.

Your job is to transform a structured list of compliance findings into a
polished, executive-ready Markdown audit report.

Report structure (use these H2 headers in order):
  ## Executive Summary
  ## Audit Scope & Methodology
  ## Risk Matrix
  ## Detailed Findings
  ## Recommendations
  ## Appendix: Evidence References

Style rules:
- Professional, confident consulting tone (Big Four style).
- Risk Matrix must be a Markdown table with columns:
  Finding ID | Title | Category | Severity | Status
- Each finding in Detailed Findings must include:
  - The verbatim evidence quote (block-quoted).
  - Page number reference.
  - Mitigation suggestion.
- Never invent facts not present in the findings JSON.
- Output ONLY the Markdown report. No JSON, no preamble.
""".strip()
# src/agents/llm_reasoner.py
import os
import json
from typing import Any, Dict, List, Optional
from src.agents.schemas import AgentResult

# Google Gemini SDK — pip install google-generativeai
try:
    import google.generativeai as genai
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
    _model = genai.GenerativeModel("gemini-1.5-flash")
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    _model = None


# ── Core LLM call ─────────────────────────────────────────────────────────────

def _call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> str:
    """
    Single Gemini call. Returns the text response.
    Falls back to a rule-based stub if SDK not available or key missing.
    """
    if not LLM_AVAILABLE or not _model:
        return _stub_response(user_prompt)

    try:
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        response = _model.generate_content(
            full_prompt,
            generation_config=genai.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=0.2,   # low temp for consistent compliance analysis
            ),
        )
        return response.text
    except Exception as e:
        return _stub_response(user_prompt)


def _call_llm_json(system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> Dict:
    """
    Gemini call that expects JSON back. Parses and returns the dict.
    """
    raw = _call_llm(
        system_prompt + "\n\nYou must respond with valid JSON only. No explanation, no markdown fences.",
        user_prompt,
        max_tokens,
    )
    # Strip markdown code fences if Gemini adds them anyway
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


# ── Compliance Analysis ───────────────────────────────────────────────────────

def analyze_compliance_document(
    document_text: str,
    standard: str,
    vendor_name: str = "the vendor",
) -> Dict[str, Any]:
    """
    Gemini reads a compliance document and extracts structured findings.
    Understands meaning — not just keywords.
    """
    system = f"""You are a senior compliance analyst specializing in {standard}.
You read vendor compliance documents and extract structured findings.
You understand regulatory language, even when exact keywords are absent.
You cite exact sentences as evidence.
Always respond in JSON."""

    user = f"""Analyze this document for {standard} compliance.
Vendor: {vendor_name}

DOCUMENT:
{document_text[:6000]}

Respond with this exact JSON structure:
{{
  "standard": "{standard}",
  "vendor": "{vendor_name}",
  "overall_compliant": true or false,
  "confidence": 0.0 to 1.0,
  "risk_level": "low" or "medium" or "high" or "critical",
  "findings": [
    {{
      "control": "control name",
      "status": "pass" or "fail" or "partial" or "not_mentioned",
      "evidence": "exact sentence from document or null",
      "gap": "what is missing or null if passing",
      "severity": "low" or "medium" or "high"
    }}
  ],
  "summary": "2-3 sentence plain English summary",
  "recommendation": "approve" or "conditional_approve" or "reject" or "request_more_docs"
}}"""

    return _call_llm_json(system, user, max_tokens=1500)


# ── Contradiction Detection ───────────────────────────────────────────────────

def detect_contradictions(
    document_text: str,
    vendor_name: str = "the vendor",
) -> Dict[str, Any]:
    """
    Gemini checks if a document contradicts itself.
    Example: claims ISO27001 certified but describes no audit process.
    """
    system = """You are a compliance auditor who specializes in finding
inconsistencies and contradictions in vendor documents.
Respond in JSON only."""

    user = f"""Review this vendor document for internal contradictions,
inconsistencies, or claims that seem unlikely to be true.

Vendor: {vendor_name}

DOCUMENT:
{document_text[:5000]}

Respond with:
{{
  "contradictions_found": true or false,
  "contradiction_count": integer,
  "items": [
    {{
      "claim_a": "first claim from document",
      "claim_b": "contradicting claim from document",
      "explanation": "why these contradict",
      "severity": "low" or "medium" or "high"
    }}
  ],
  "trust_score": 0.0 to 1.0,
  "notes": "overall assessment"
}}"""

    return _call_llm_json(system, user, max_tokens=1000)


# ── Evidence Extraction ───────────────────────────────────────────────────────

def extract_evidence(
    document_text: str,
    control: str,
    vendor_name: str = "the vendor",
) -> Dict[str, Any]:
    """
    Gemini finds the exact sentence(s) proving or disproving a compliance
    control — even when phrased completely differently in the document.
    """
    system = """You are a compliance evidence extractor.
Given a control requirement, you find the exact supporting or refuting
sentences in a document, even when the wording differs from the control name.
Respond in JSON only."""

    user = f"""Find evidence for or against this compliance control:
CONTROL: {control}
VENDOR: {vendor_name}

DOCUMENT:
{document_text[:5000]}

Respond with:
{{
  "control": "{control}",
  "evidence_found": true or false,
  "evidence_type": "supports" or "refutes" or "partial" or "absent",
  "exact_sentences": ["sentence 1 from doc", "sentence 2 from doc"],
  "paraphrase": "what the document actually says about this in plain English",
  "confidence": 0.0 to 1.0,
  "location_hint": "approximate location like 'Section 3' or 'Page 4' if detectable, else null"
}}"""

    return _call_llm_json(system, user, max_tokens=800)


# ── Risk Narrative ────────────────────────────────────────────────────────────

def generate_risk_narrative(
    vendor_name: str,
    compliance_findings: List[Dict],
    contradiction_findings: Dict,
) -> str:
    """
    Gemini writes a human-readable risk narrative for the compliance report.
    """
    system = """You are a senior compliance officer writing a vendor risk assessment.
Write clearly, professionally, and concisely.
Your audience is a procurement committee making an approval decision."""

    user = f"""Write a vendor risk narrative for: {vendor_name}

Compliance findings:
{json.dumps(compliance_findings, indent=2)[:3000]}

Contradiction analysis:
{json.dumps(contradiction_findings, indent=2)[:1000]}

Write a 3-paragraph risk narrative:
1. Overall compliance posture
2. Key risks and gaps found
3. Recommendation with conditions if any

Be specific. Reference actual findings. Do not use filler language."""

    return _call_llm(system, user, max_tokens=600)


# ── Stub fallback (when no API key or SDK) ────────────────────────────────────

def _stub_response(prompt: str) -> str:
    """Returns a minimal valid JSON stub when Gemini is unavailable."""
    return json.dumps({
        "overall_compliant": False,
        "confidence": 0.5,
        "risk_level": "medium",
        "findings": [],
        "summary": "Gemini LLM not available — stub response returned.",
        "recommendation": "request_more_docs",
        "contradictions_found": False,
        "contradiction_count": 0,
        "items": [],
        "trust_score": 0.5,
        "notes": "Gemini unavailable",
        "evidence_found": False,
        "evidence_type": "absent",
        "exact_sentences": [],
        "paraphrase": "Gemini unavailable",
        "location_hint": None,
    })
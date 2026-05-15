"""
src/agents/llm_reasoner.py
───────────────────────────
Gemini LLM wrapper for compliance reasoning.
All agent LLM calls go through this file.
"""

import os
import json
from typing import Any, Dict, List, Optional

# ── Gemini SDK initialization ─────────────────────────────────────────────────

try:
    from google import genai
    from google.genai import types
    LLM_AVAILABLE = False
    _client = None

    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key and api_key.strip():
        try:
            _client = genai.Client(api_key=api_key)
            LLM_AVAILABLE = True
            print("✓ Gemini initialized successfully")
        except Exception as e:
            print(f"✗ Gemini init failed: {e}")
            LLM_AVAILABLE = False
    else:
        print("✗ GEMINI_API_KEY not set in environment")
        LLM_AVAILABLE = False

except ImportError as e:
    print(f"✗ google.genai import failed: {e}")
    LLM_AVAILABLE = False
    _client = None


# ── Core LLM caller ───────────────────────────────────────────────────────────

def _call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 2048) -> str:
    """
    Single Gemini call. Returns the text response.
    Falls back to a stub string if SDK not available or key missing.
    """
    if not LLM_AVAILABLE or not _client:
        print("LLM not available, returning stub")
        return _stub_response(user_prompt)

    try:
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        print(f"Calling Gemini ({len(full_prompt)} chars)...")
        response = _client.models.generate_content(
            model="gemini-2.5-flash",
            contents=full_prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=max_tokens,
                temperature=0.2,
            ),
        )
        print(f"Gemini responded: {response.text[:80]}...")
        return response.text

    except Exception as e:
        print(f"Gemini call failed: {type(e).__name__}: {e}")
        return _stub_response(user_prompt)


# ── JSON wrapper ──────────────────────────────────────────────────────────────

def _call_llm_json(system_prompt: str, user_prompt: str, max_tokens: int = 2048) -> Dict:
    """
    Gemini call that expects JSON back.
    Robust parser handles markdown fences and truncated responses.
    """
    raw = _call_llm(
        system_prompt + (
            "\n\nYou MUST respond with valid JSON only. "
            "No markdown, no code fences, no explanation. "
            "Start with { and end with }"
        ),
        user_prompt,
        max_tokens,
    )

    raw = raw.strip()

    # Strip markdown code fences if Gemini added them anyway
    if "```" in raw:
        parts = raw.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                raw = part
                break

    # Attempt to repair truncated JSON (happens when max_tokens is too low)
    if not raw.endswith("}"):
        open_count  = raw.count("{") - raw.count("}")
        open_arrays = raw.count("[") - raw.count("]")
        # Close any unterminated string
        if raw.count('"') % 2 != 0:
            raw += '"'
        raw += "]" * max(0, open_arrays)
        raw += "}" * max(0, open_count)

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"JSON parse error after repair: {e}")
        print(f"Raw (first 300 chars): {raw[:300]}")
        return _default_stub()


# ── Default stub ──────────────────────────────────────────────────────────────

def _default_stub() -> Dict:
    """Returned whenever JSON parsing fails completely."""
    return {
        "overall_compliant":    False,
        "confidence":           0.5,
        "risk_level":           "medium",
        "findings":             [],
        "summary":              "LLM response could not be parsed. Manual review required.",
        "recommendation":       "request_more_docs",
        "contradictions_found": False,
        "contradiction_count":  0,
        "items":                [],
        "trust_score":          0.5,
        "notes":                "JSON parse error — stub returned",
        "evidence_found":       False,
        "evidence_type":        "absent",
        "exact_sentences":      [],
        "paraphrase":           "Parse error",
        "location_hint":        None,
        # ← this key was missing before — caused KeyError: 'risk_narrative'
        "risk_narrative":       "Risk narrative unavailable — LLM response failed to parse.",
    }


def _stub_response(prompt: str) -> str:
    """Returns a minimal valid JSON stub string when Gemini is unavailable."""
    return json.dumps({
        "overall_compliant":    False,
        "confidence":           0.5,
        "risk_level":           "medium",
        "findings":             [],
        "summary":              "Gemini LLM not available — stub response returned.",
        "recommendation":       "request_more_docs",
        "contradictions_found": False,
        "contradiction_count":  0,
        "items":                [],
        "trust_score":          0.5,
        "notes":                "Gemini unavailable",
        "evidence_found":       False,
        "evidence_type":        "absent",
        "exact_sentences":      [],
        "paraphrase":           "Gemini unavailable",
        "location_hint":        None,
        "risk_narrative":       "Risk narrative unavailable — Gemini not configured.",
    })


# ── Compliance Analysis ───────────────────────────────────────────────────────

def analyze_compliance_document(
    document_text: str,
    standard: str,
    vendor_name: str = "the vendor",
) -> Dict[str, Any]:
    """
    Gemini reads a compliance document and extracts structured findings.
    """
    system = (
        f"You are a senior compliance analyst specializing in {standard}. "
        "Extract structured findings from vendor documents. "
        "ALWAYS respond with VALID JSON ONLY. No markdown, no explanation."
    )

    user = f"""Analyze for {standard} compliance.
Vendor: {vendor_name}

DOCUMENT:
{document_text[:4000]}

Respond ONLY with this JSON structure (fill in real values):
{{
  "standard": "{standard}",
  "vendor": "{vendor_name}",
  "overall_compliant": true,
  "confidence": 0.8,
  "risk_level": "low",
  "findings": [
    {{
      "control": "encryption",
      "status": "pass",
      "evidence": "exact quote from document",
      "gap": null,
      "severity": "low"
    }}
  ],
  "summary": "one sentence summary",
  "recommendation": "approve"
}}"""

    # 3000 tokens — gives Gemini room to finish the JSON without truncating
    return _call_llm_json(system, user, max_tokens=3000)


# ── Contradiction Detection ───────────────────────────────────────────────────

def detect_contradictions(
    document_text: str,
    vendor_name: str = "the vendor",
) -> Dict[str, Any]:
    """
    Gemini checks if a document contradicts itself.
    Example: claims ISO27001 certified but describes no audit process.
    """
    system = (
        "You are a compliance auditor who specializes in finding "
        "inconsistencies and contradictions in vendor documents. "
        "Respond in JSON only."
    )

    user = f"""Review this vendor document for internal contradictions,
inconsistencies, or claims that seem unlikely to be true.

Vendor: {vendor_name}

DOCUMENT:
{document_text[:5000]}

Respond with:
{{
  "contradictions_found": true,
  "contradiction_count": 1,
  "items": [
    {{
      "claim_a": "first claim from document",
      "claim_b": "contradicting claim from document",
      "explanation": "why these contradict",
      "severity": "medium"
    }}
  ],
  "trust_score": 0.8,
  "notes": "overall assessment"
}}"""

    return _call_llm_json(system, user, max_tokens=1500)


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
    system = (
        "You are a compliance evidence extractor. "
        "Given a control requirement, find the exact supporting or refuting "
        "sentences in a document, even when the wording differs from the control name. "
        "Respond in JSON only."
    )

    user = f"""Find evidence for or against this compliance control:
CONTROL: {control}
VENDOR: {vendor_name}

DOCUMENT:
{document_text[:5000]}

Respond with:
{{
  "control": "{control}",
  "evidence_found": true,
  "evidence_type": "supports",
  "exact_sentences": ["sentence 1 from doc"],
  "paraphrase": "what the document says about this in plain English",
  "confidence": 0.9,
  "location_hint": "Section 3"
}}"""

    return _call_llm_json(system, user, max_tokens=1000)


# ── Risk Narrative ────────────────────────────────────────────────────────────

def generate_risk_narrative(
    vendor_name: str,
    compliance_findings: List[Dict],
    contradiction_findings: Dict,
) -> str:
    """
    Gemini writes a human-readable risk narrative for the compliance report.
    Returns plain text (not JSON).
    """
    system = (
        "You are a senior compliance officer writing a vendor risk assessment. "
        "Write clearly, professionally, and concisely. "
        "Your audience is a procurement committee making an approval decision."
    )

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

    # Returns plain text — no JSON parsing needed
    return _call_llm(system, user, max_tokens=800)
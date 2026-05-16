"""
src/tools/mcp_bridge.py
────────────────────────
Phase 2: MCP Bridge Layer

All external tool calls pass through call_tool(). This single chokepoint
lets P3 (HITL / State) intercept HIGH_RISK_TOOLS before they execute,
and lets P1 (Orchestrator) record every tool invocation in the audit trail.

Concrete adapters
-----------------
  _call_ocr_unstructured  → POST https://api.unstructured.io/general/v0/general
  _call_ocr_textract      → boto3 textract start_document_analysis
  _call_kyc_opencorporates→ GET  https://api.opencorporates.com/v0.4/companies/search
  _call_aml_sanctions_io  → POST https://api.sanctions.io/v1/screen
  _call_qdrant_search     → qdrant_client.search()

All other tools (web_search, pdf_reader, …) fall through to _call_generic(),
which is a stub you replace with real implementations as the service grows.

Environment variables expected (via python-dotenv or ECS task role):
  UNSTRUCTURED_API_KEY
  AWS_DEFAULT_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
  OPENCORPORATES_API_KEY
  SANCTIONS_IO_API_KEY
  QDRANT_URL, QDRANT_API_KEY
"""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict

import httpx                        # pip install httpx
from qdrant_client import QdrantClient          # pip install qdrant-client
from qdrant_client.http.models import Filter, FieldCondition, MatchValue

log = logging.getLogger(__name__)

# ── Clients (lazy-initialised) ────────────────────────────────────────────────

_qdrant: QdrantClient | None = None


def _get_qdrant() -> QdrantClient:
    global _qdrant
    if _qdrant is None:
        _qdrant = QdrantClient(
            url=os.environ["QDRANT_URL"],
            api_key=os.environ.get("QDRANT_API_KEY"),
        )
    return _qdrant


# ── Public API ────────────────────────────────────────────────────────────────

def call_tool(tool_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dispatch to the correct adapter and return a standardised result dict.

    All results include:
      _tool       : name of the tool called
      _called_at  : ISO 8601 UTC timestamp
      _payload_hash: SHA-256 of the input payload (for audit trail)

    Raises RuntimeError on unrecoverable adapter errors (P1 catches these).
    """
    log.info("mcp_bridge: calling tool=%r", tool_name)

    adapters = {
        "ocr_unstructured":      _call_ocr_unstructured,
        "ocr_textract":          _call_ocr_textract,
        "kyc_opencorporates":    _call_kyc_opencorporates,
        "aml_sanctions_io":      _call_aml_sanctions_io,
        "qdrant_evidence_search":_call_qdrant_search,
    }

    adapter = adapters.get(tool_name, _call_generic)
    raw_result = adapter(payload)

    # Attach audit metadata to every result
    raw_result["_tool"]         = tool_name
    raw_result["_called_at"]    = datetime.now(timezone.utc).isoformat()
    raw_result["_payload_hash"] = _sha256(payload)
    return raw_result


# ── OCR adapters ──────────────────────────────────────────────────────────────

def _call_ocr_unstructured(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    POST to Unstructured.io /general endpoint.
    Returns structured elements + table list.
    """
    api_key   = os.environ["UNSTRUCTURED_API_KEY"]
    file_path = payload["file_path"]
    strategy  = payload.get("strategy", "auto")

    with open(file_path, "rb") as fh:
        response = httpx.post(
            "https://api.unstructured.io/general/v0/general",
            headers={"unstructured-api-key": api_key},
            files={"files": (os.path.basename(file_path), fh, "application/pdf")},
            data={"strategy": strategy, "output_format": "application/json"},
            timeout=120.0,
        )
    response.raise_for_status()
    elements = response.json()

    tables = [e for e in elements if e.get("type") == "Table"]
    page_count = max(
        (e.get("metadata", {}).get("page_number", 1) for e in elements),
        default=1,
    )

    return {"elements": elements, "tables": tables, "page_count": page_count}


def _call_ocr_textract(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Kick off an AWS Textract async analysis job and poll for results.
    Returns raw blocks + mean confidence.
    """
    import boto3  # pip install boto3

    client      = boto3.client("textract", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
    s3_bucket   = payload["s3_bucket"]
    s3_key      = payload["s3_key"]
    feature_types = payload.get("feature_types", ["TABLES", "FORMS"])

    start_resp = client.start_document_analysis(
        DocumentLocation={"S3Object": {"Bucket": s3_bucket, "Name": s3_key}},
        FeatureTypes=feature_types,
    )
    job_id = start_resp["JobId"]
    log.info("textract: job_id=%s", job_id)

    # Poll (simple blocking wait — in prod, use SQS/SNS notification instead)
    import time
    blocks: list = []
    next_token = None
    while True:
        kwargs: Dict[str, Any] = {"JobId": job_id}
        if next_token:
            kwargs["NextToken"] = next_token
        result = client.get_document_analysis(**kwargs)
        status = result["JobStatus"]

        if status == "IN_PROGRESS":
            time.sleep(5)
            continue
        if status == "FAILED":
            raise RuntimeError(f"Textract job {job_id} failed: {result.get('StatusMessage')}")

        blocks.extend(result.get("Blocks", []))
        next_token = result.get("NextToken")
        if not next_token:
            break

    confidences = [b.get("Confidence", 100.0) for b in blocks if "Confidence" in b]
    mean_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    return {"blocks": blocks, "confidence": round(mean_confidence, 2)}


# ── External verification adapters ────────────────────────────────────────────

def _call_kyc_opencorporates(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    GET https://api.opencorporates.com/v0.4/companies/search
    Returns best-match company + confidence score.
    """
    api_key       = os.environ["OPENCORPORATES_API_KEY"]
    company_name  = payload["company_name"]
    jurisdiction  = payload.get("jurisdiction", "")
    company_number= payload.get("company_number", "")

    params: Dict[str, Any] = {
        "q":          company_name,
        "api_token":  api_key,
        "format":     "json",
    }
    if jurisdiction:
        params["jurisdiction_code"] = jurisdiction
    if company_number:
        params["company_number"] = company_number

    resp = httpx.get(
        "https://api.opencorporates.com/v0.4/companies/search",
        params=params,
        timeout=30.0,
    )
    resp.raise_for_status()
    data = resp.json()

    companies = data.get("results", {}).get("companies", [])
    if not companies:
        return {"matched": False, "company": {}, "confidence_score": 0.0, "source_url": ""}

    best = companies[0]["company"]
    name_match = _name_similarity(company_name, best.get("name", ""))

    return {
        "matched":          True,
        "company":          best,
        "confidence_score": round(name_match, 3),
        "source_url":       best.get("opencorporates_url", ""),
    }


def _call_aml_sanctions_io(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    POST https://api.sanctions.io/v1/screen
    Returns is_sanctioned flag + risk score + matched list entries.
    """
    api_key     = os.environ["SANCTIONS_IO_API_KEY"]
    entity_name = payload["entity_name"]
    entity_type = payload.get("entity_type", "company")
    country     = payload.get("country", "")
    dob         = payload.get("dob")  # optional

    body: Dict[str, Any] = {
        "name":        entity_name,
        "entity_type": entity_type,
    }
    if country:
        body["country"] = country
    if dob:
        body["date_of_birth"] = dob

    resp = httpx.post(
        "https://api.sanctions.io/v1/screen",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
        },
        json=body,
        timeout=30.0,
    )
    resp.raise_for_status()
    data = resp.json()

    hits          = data.get("hits", [])
    risk_score    = data.get("risk_score", 0.0)
    is_sanctioned = risk_score > 0.5 or bool(hits)

    return {
        "is_sanctioned": is_sanctioned,
        "risk_score":    round(risk_score, 3),
        "matched_lists": hits,
        "checked_at":    datetime.now(timezone.utc).isoformat(),
    }


# ── Qdrant evidence retrieval ─────────────────────────────────────────────────

def _call_qdrant_search(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Semantic search over the tenant's Qdrant evidence collection.
    Embeds the query with a lightweight model before searching.
    """
    import numpy as np                                  # pip install numpy
    from sentence_transformers import SentenceTransformer  # pip install sentence-transformers

    query      = payload["query"]
    tenant_id  = payload["tenant_id"]
    collection = payload.get("collection", "vendor_evidence")
    top_k      = int(payload.get("top_k", 5))
    category   = payload.get("category")              # optional filter

    # Embed the query (model cached after first load)
    model  = SentenceTransformer("all-MiniLM-L6-v2")
    vector = model.encode(query).tolist()

    # Build category filter if requested
    query_filter = None
    if category:
        query_filter = Filter(
            must=[FieldCondition(key="category", match=MatchValue(value=category))]
        )

    client = _get_qdrant()
    hits = client.search(
        collection_name=f"{tenant_id}_{collection}",
        query_vector=vector,
        limit=top_k,
        query_filter=query_filter,
        with_payload=True,
    )

    return {
        "hits": [
            {
                "score":   round(h.score, 4),
                "payload": h.payload,     # {quote, page_number, source_hash, category}
            }
            for h in hits
        ]
    }


# ── Generic fallback ──────────────────────────────────────────────────────────

def _call_generic(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stub for tools not yet wired to a real backend (web_search, pdf_reader, etc.).
    In production, replace with actual implementations or import from existing adapters.
    """
    log.warning("mcp_bridge: _call_generic hit — no real adapter for this tool")
    return {"status": "stub", "payload_received": payload}


# ── Utility ───────────────────────────────────────────────────────────────────

def _sha256(obj: Any) -> str:
    import json
    raw = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def _name_similarity(a: str, b: str) -> float:
    """
    Simple Jaccard similarity over word sets.
    Good enough to rank OpenCorporates results without an LLM call.
    """
    set_a = set(a.lower().split())
    set_b = set(b.lower().split())
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)
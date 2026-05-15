"""
src/tools/registry.py
─────────────────────
Phase 2: Compliance Tool Registry
Extends the base registry with compliance-specific tools:
  - OCR / Document Bridge  (Unstructured.io or AWS Textract)
  - External Verification  (KYC via OpenCorporates, AML via Sanctions.io)
  - Pruner Logic           (task-aware tool filtering)

P1 (Orchestrator) imports `registry` to resolve tools per audit node.
P3 (HITL / State)  imports `HIGH_RISK_TOOLS` to gate human approval.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set


# ── Schema ────────────────────────────────────────────────────────────────────

@dataclass
class ToolMeta:
    name: str
    description: str
    allowed_tenants: List[str]          # ["*"] means all tenants
    input_schema: Dict[str, str]
    output_schema: Dict[str, str]
    categories: List[str] = field(default_factory=list)  # e.g. ["financial", "security"]
    cost_tier: str = "low"              # low | medium | high  (used by pruner)


# ── Tool Definitions ──────────────────────────────────────────────────────────

RAW_TOOLS: List[Dict] = [

    # ── Pre-existing general tools ────────────────────────────────────────────
    {
        "name": "web_search",
        "description": "Search the web for recent information on a topic",
        "allowed_tenants": ["*"],
        "input_schema":  {"query": "string"},
        "output_schema": {"results": "list"},
        "categories":    ["general"],
        "cost_tier":     "low",
    },
    {
        "name": "crm_lookup",
        "description": "Fetch customer records from CRM by customer ID or email",
        "allowed_tenants": ["tenant_demo", "tenant_acme"],
        "input_schema":  {"customer_id": "string"},
        "output_schema": {"customer": "object"},
        "categories":    ["general"],
        "cost_tier":     "low",
    },
    {
        "name": "send_email",
        "description": "Send an email to a recipient with subject and body",
        "allowed_tenants": ["*"],
        "input_schema":  {"to": "string", "subject": "string", "body": "string"},
        "output_schema": {"sent": "bool"},
        "categories":    ["general"],
        "cost_tier":     "low",
    },
    {
        "name": "pdf_reader",
        "description": "Extract text content from a PDF file (basic, no table awareness)",
        "allowed_tenants": ["*"],
        "input_schema":  {"file_path": "string"},
        "output_schema": {"text": "string"},
        "categories":    ["document"],
        "cost_tier":     "low",
    },
    {
        "name": "database_write",
        "description": "Write or update a record in the internal database",
        "allowed_tenants": ["tenant_acme"],
        "input_schema":  {"table": "string", "record": "object"},
        "output_schema": {"success": "bool"},
        "categories":    ["general"],
        "cost_tier":     "low",
    },
    {
        "name": "slack_notify",
        "description": "Send a Slack message to a channel",
        "allowed_tenants": ["*"],
        "input_schema":  {"channel": "string", "message": "string"},
        "output_schema": {"ok": "bool"},
        "categories":    ["general"],
        "cost_tier":     "low",
    },

    # ── Phase 2: OCR / Document Bridge ───────────────────────────────────────
    {
        "name": "ocr_unstructured",
        "description": (
            "OCR bridge to Unstructured.io. Converts messy PDFs/SOC2 reports into "
            "structured JSON with table-awareness. Returns pages, tables, and text blocks "
            "with bounding-box metadata. Preferred for SOC2, ISO27001, and complex layouts."
        ),
        "allowed_tenants": ["*"],
        "input_schema": {
            "file_path":    "string",   # local path or S3 URI
            "strategy":     "string",   # 'auto' | 'hi_res' | 'ocr_only'
            "output_format":"string",   # 'json' | 'text'
        },
        "output_schema": {
            "elements":     "list",     # [{type, text, metadata: {page_number, ...}}]
            "tables":       "list",     # [{rows: [[cell, ...]], page_number}]
            "page_count":   "int",
        },
        "categories": ["document", "security", "privacy", "availability", "financial"],
        "cost_tier":  "medium",
    },
    {
        "name": "ocr_textract",
        "description": (
            "OCR bridge to AWS Textract. Falls back from Unstructured.io for scanned "
            "documents with handwritten annotations or complex multi-column layouts. "
            "Returns raw blocks with confidence scores."
        ),
        "allowed_tenants": ["*"],
        "input_schema": {
            "s3_bucket":    "string",
            "s3_key":       "string",
            "feature_types":"list",     # ['TABLES', 'FORMS', 'SIGNATURES']
        },
        "output_schema": {
            "blocks":       "list",     # AWS Textract block format
            "confidence":   "float",    # mean confidence across all blocks
        },
        "categories": ["document", "security", "privacy", "availability", "financial"],
        "cost_tier":  "medium",
    },

    # ── Phase 2: External Verification (KYC / AML) ────────────────────────────
    {
        "name": "kyc_opencorporates",
        "description": (
            "MCP bridge to OpenCorporates API. Verifies corporate entity existence, "
            "registered address, officers, and filing history. Used by the_judge during "
            "KYC audits to cross-check vendor-claimed company details."
        ),
        "allowed_tenants": ["*"],
        "input_schema": {
            "company_name":    "string",
            "jurisdiction":    "string",   # ISO 3166-1 alpha-2, e.g. 'us_de', 'gb'
            "company_number":  "string",   # optional — narrows search
        },
        "output_schema": {
            "matched":         "bool",
            "company":         "object",   # {name, number, jurisdiction, officers, ...}
            "confidence_score":"float",
            "source_url":      "string",
        },
        "categories": ["kyc", "financial"],
        "cost_tier":  "medium",
    },
    {
        "name": "aml_sanctions_io",
        "description": (
            "MCP bridge to Sanctions.io. Screens vendors and individuals against OFAC, "
            "UN, EU, and HM Treasury sanctions lists. Returns hit probability and matched "
            "list entries. Used by the_judge in AML / financial-risk audits."
        ),
        "allowed_tenants": ["*"],
        "input_schema": {
            "entity_name":    "string",
            "entity_type":    "string",   # 'individual' | 'company'
            "country":        "string",   # ISO 3166-1 alpha-2
            "dob":            "string",   # optional, 'YYYY-MM-DD', for individuals
        },
        "output_schema": {
            "is_sanctioned":  "bool",
            "risk_score":     "float",    # 0.0 – 1.0
            "matched_lists":  "list",     # [{"list": "OFAC", "entry": {...}}]
            "checked_at":     "string",   # ISO 8601 timestamp
        },
        "categories": ["aml", "financial"],
        "cost_tier":  "high",
    },

    # ── Phase 2: Qdrant Evidence Retrieval ───────────────────────────────────
    {
        "name": "qdrant_evidence_search",
        "description": (
            "Semantic search over the tenant's Qdrant evidence vault. Returns Memory Cards "
            "(source_hash, quote, page_number, category) most relevant to a compliance query. "
            "Used by the_reader to retrieve prior audit findings for the same vendor."
        ),
        "allowed_tenants": ["*"],
        "input_schema": {
            "query":        "string",
            "tenant_id":    "string",
            "collection":   "string",   # e.g. 'vendor_evidence'
            "top_k":        "int",      # default 5
            "category":     "string",   # optional filter: 'security' | 'privacy' | ...
        },
        "output_schema": {
            "hits": "list",             # [{score, payload: {quote, page_number, source_hash}}]
        },
        "categories": ["security", "privacy", "availability", "financial", "kyc", "aml"],
        "cost_tier":  "low",
    },
    # Add these to RAW_TOOLS list:
{
    "name": "pdf_extractor",
    "description": "Extract and parse compliance documents SOC2 ISO certificates AML KYC privacy policy contracts",
    "allowed_tenants": ["*"],
    "input_schema": {"file_path": "string", "doc_type": "string"},
    "output_schema": {"extracted_text": "string", "sections": "object"},
},
{
    "name": "compliance_checker",
    "description": "Check vendor compliance against SOC2 ISO27001 AML KYC regulatory standards requirements",
    "allowed_tenants": ["tenant_jpmorgan", "tenant_goldman", "tenant_stripe", "tenant_razorpay"],
    "input_schema": {"vendor_id": "string", "standard": "string", "document_text": "string"},
    "output_schema": {"compliant": "bool", "gaps": "list", "risk_score": "string"},
},
{
    "name": "risk_scorer",
    "description": "Score vendor risk level based on security encryption privacy financial stability",
    "allowed_tenants": ["*"],
    "input_schema": {"vendor_data": "object"},
    "output_schema": {"risk_score": "string", "flags": "list", "recommendation": "string"},
},
{
    "name": "contract_analyzer",
    "description": "Analyze vendor contracts SLA terms liability clauses legal obligations",
    "allowed_tenants": ["tenant_jpmorgan", "tenant_goldman"],
    "input_schema": {"contract_text": "string"},
    "output_schema": {"key_clauses": "list", "red_flags": "list", "summary": "string"},
},
{
    "name": "report_generator",
    "description": "Generate vendor onboarding compliance report summary for procurement legal team",
    "allowed_tenants": ["*"],
    "input_schema": {"vendor_id": "string", "findings": "object"},
    "output_schema": {"report": "string", "approved": "bool"},
},
{
    "name": "vendor_database_lookup",
    "description": "Lookup existing vendor records sanctions lists blacklists financial history",
    "allowed_tenants": ["tenant_jpmorgan", "tenant_goldman", "tenant_stripe"],
    "input_schema": {"vendor_name": "string", "vendor_id": "string"},
    "output_schema": {"vendor_record": "object", "sanctions_hit": "bool"},
},
]


# ── Risk Gates ────────────────────────────────────────────────────────────────

# P3 (HITL) imports this set to decide whether to pause the DAG for human approval.
HIGH_RISK_TOOLS: Set[str] = {
    "send_email",
    "database_write",
    "aml_sanctions_io",    # results may trigger legal/regulatory action
}

# P1 (Orchestrator) uses this to decide which tool is preferred for OCR.
OCR_PREFERENCE_ORDER: List[str] = ["ocr_unstructured", "ocr_textract"]

# Mapping: compliance category → tool names that are relevant
CATEGORY_TOOL_MAP: Dict[str, List[str]] = {
    "security":     ["ocr_unstructured", "ocr_textract", "qdrant_evidence_search"],
    "privacy":      ["ocr_unstructured", "ocr_textract", "qdrant_evidence_search"],
    "availability": ["ocr_unstructured", "ocr_textract", "qdrant_evidence_search"],
    "financial":    ["ocr_unstructured", "ocr_textract", "kyc_opencorporates",
                     "aml_sanctions_io", "qdrant_evidence_search"],
    "kyc":          ["kyc_opencorporates", "qdrant_evidence_search"],
    "aml":          ["aml_sanctions_io",  "qdrant_evidence_search"],
    "general":      ["web_search", "pdf_reader"],
}


# ── Registry Class ────────────────────────────────────────────────────────────

class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, ToolMeta] = {}
        self._load()

    def _load(self) -> None:
        for raw in RAW_TOOLS:
            self._tools[raw["name"]] = ToolMeta(**raw)

    # ── Basic accessors ───────────────────────────────────────────────────────

    def get_all(self) -> List[ToolMeta]:
        return list(self._tools.values())

    def get_by_name(self, name: str) -> ToolMeta:
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not in registry")
        return self._tools[name]

    def get_for_tenant(self, tenant_id: str) -> List[ToolMeta]:
        return [
            t for t in self._tools.values()
            if "*" in t.allowed_tenants or tenant_id in t.allowed_tenants
        ]

    # ── Phase 2: Category-aware filtering (Pruner support) ────────────────────

    def get_for_category(self, category: str) -> List[ToolMeta]:
        """
        Return tools whose `categories` list includes `category`.
        Used by pruner.py to build the focused tool window for a given audit node.
        """
        return [t for t in self._tools.values() if category in t.categories]

    def get_for_task(self, task: str, tenant_id: str) -> List[ToolMeta]:
        """
        Convenience: resolve category from task keyword and intersect with tenant access.
        The pruner calls this; agents should call pruner.prune_tools() instead.
        """
        category = _infer_category(task)
        allowed_names = {t.name for t in self.get_for_tenant(tenant_id)}
        category_tools = self.get_for_category(category)
        return [t for t in category_tools if t.name in allowed_names]

    def is_high_risk(self, tool_name: str) -> bool:
        return tool_name in HIGH_RISK_TOOLS


def _infer_category(task: str) -> str:
    """
    Lightweight keyword → category mapper.
    The pruner uses this so we don't need an LLM call just to pick tools.
    """
    task_lower = task.lower()
    if any(k in task_lower for k in ("sanction", "aml", "money launder")):
        return "aml"
    if any(k in task_lower for k in ("kyc", "know your customer", "corporate", "entity")):
        return "kyc"
    if any(k in task_lower for k in ("financial", "risk", "revenue", "payment", "bank")):
        return "financial"
    if any(k in task_lower for k in ("privacy", "gdpr", "pii", "data subject", "ccpa")):
        return "privacy"
    if any(k in task_lower for k in ("availab", "uptime", "sla", "disaster", "recovery", "rto")):
        return "availability"
    if any(k in task_lower for k in ("security", "encrypt", "access control", "vuln", "pentest")):
        return "security"
    return "general"


# Single shared instance — all modules import this object, not the class.
registry = ToolRegistry()
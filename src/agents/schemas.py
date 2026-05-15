"""
src/agents/schemas.py
──────────────────────
Phase 2: Shared Pydantic schemas for all compliance agents.

These are the canonical data contracts between:
  runtime.py  (agent execution)
  orchestrator.py (P1 DAG nodes)
  state.py / hitl.py (P3 audit trail)
  dashboard (P4 display)
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field
from typing import Literal, Optional, List, Dict, Any


# ── Tool schema (also used by registry.py) ────────────────────────────────────

class ToolMeta(BaseModel):
    name: str
    description: str
    allowed_tenants: List[str]
    input_schema: Dict[str, str]
    output_schema: Dict[str, str]
    categories: List[str] = Field(default_factory=list)
    cost_tier: str = "low"                  # low | medium | high


# ── Evidence / Memory Card ────────────────────────────────────────────────────

class EvidenceCard(BaseModel):
    """
    The atomic unit of evidence. Every fact the_reader extracts is stored as one.
    Cryptographically linked to its source via source_hash (SHA-256 of the raw PDF bytes).
    P3 (state.py) persists these to Qdrant and Postgres.
    """
    quote: str                              # Verbatim extract from the source document
    page_number: int
    source_hash: str                        # SHA-256 of the raw source file
    source_filename: str
    category: str                           # security | privacy | availability | financial | kyc | aml
    relevance_score: float = 1.0            # 0–1; populated by the_reader
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── Finding ───────────────────────────────────────────────────────────────────

class Finding(BaseModel):
    """
    A single non-compliance observation raised by the_judge.
    Maps 1-to-1 to a row in the "Gap Analysis" table (DAG Node D).
    """
    finding_id: str                         # UUID, set by the_judge
    category: str                           # compliance category
    severity: str                           # critical | high | medium | low | info
    title: str                              # Short description, e.g. "MFA not enforced"
    detail: str                             # Full adversarial reasoning
    evidence: List[EvidenceCard]            # Supporting quotes from the_reader
    mitigation_suggestion: str = ""         # Populated by DAG Node D (Gap Analysis)
    is_confirmed: bool = False              # Flipped to True during HITL review (P3)


# ── Agent result ──────────────────────────────────────────────────────────────

class AgentResult(BaseModel):
    """
    Unified return type for all three agents (the_reader, the_judge, the_scribe).
    P1 stores this in Postgres at the end of each DAG node.
    """
    agent_name: str
    status: str                             # success | failed | partial
    output: Dict[str, Any]                  # agent-specific payload (see below)
    tools_used: List[str]
    error: Optional[str] = None
    duration_ms: Optional[float] = None
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Typed accessors for well-known output shapes
    def evidence_cards(self) -> List[EvidenceCard]:
        """For the_reader results."""
        raw = self.output.get("evidence_cards", [])
        return [EvidenceCard(**e) for e in raw]

    def findings(self) -> List[Finding]:
        """For the_judge results."""
        raw = self.output.get("findings", [])
        return [Finding(**f) for f in raw]

    def report_markdown(self) -> str:
        """For the_scribe results."""
        return self.output.get("report_markdown", "")


# ── Audit state (used by P1 & P3) ────────────────────────────────────────────
class VendorOnboardingRequest(BaseModel):
    tenant_id: str
    vendor_name: str
    vendor_id: str
    documents: List[str]        # list of file paths
    standards_required: List[str]  # ["SOC2", "ISO27001", "AML"]
    workflow_id: str = "vendor_onboarding"

class VendorOnboardingResult(BaseModel):
    vendor_id: str
    risk_score: str             # "low", "medium", "high"
    compliant: bool
    gaps: List[str]
    recommendation: str
    report: str
    requires_human_review: bool
class AuditState(BaseModel):
    """
    Snapshot of a single audit's lifecycle, persisted to Postgres by P3.
    The Orchestrator reads/writes this at every DAG node transition.
    """
    audit_id: str
    tenant_id: str
    vendor_name: str
    source_file_hash: str
    status: str                             # ingesting | retrieving | auditing | gap_analysis | drafting | paused | complete | failed
    current_node: str                       # A | B | C | D | E | F
    reader_result: Optional[AgentResult] = None
    judge_results: List[AgentResult] = Field(default_factory=list)
    scribe_result: Optional[AgentResult] = None
    findings: List[Finding] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    hitl_override: bool = False             # True once human reviewer approves
    hitl_notes: str = ""


    # Add these at the bottom of schemas.py:

class ComplianceFinding(BaseModel):
    control: str
    status: Literal["pass", "fail", "partial", "not_mentioned"]
    evidence: Optional[str]
    gap: Optional[str]
    severity: Literal["low", "medium", "high"]

class LLMComplianceResult(BaseModel):
    vendor: str
    standard: str
    overall_compliant: bool
    confidence: float
    risk_level: Literal["low", "medium", "high", "critical"]
    findings: List[ComplianceFinding]
    summary: str
    recommendation: Literal["approve", "conditional_approve", "reject", "request_more_docs"]
    contradictions_found: bool
    risk_narrative: str
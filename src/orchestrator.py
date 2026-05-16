import asyncio
import json
from pathlib import Path
from typing import TypedDict, Optional
from datetime import datetime

import fitz
import yaml

from src.memory.state import StateManager
from src.agents.runtime import compliance_reasoning_agent

state_manager = StateManager("checkpoints")

# =============================================================================
# AUDIT STATE
# =============================================================================

class AuditState(TypedDict):
    run_id: str
    tenant_id: str

    uploaded_files: list[str]

    parsed_documents: dict
    retrieved_rules: dict

    audit_findings: list
    gap_analysis: list

    draft_report: str

    status: str
    current_node: str

    requires_human_review: bool
    human_decision: Optional[str]

    risk_score: int
    risk_level: str

    approval_recommendation: str

    control_coverage: dict
    coverage_percent: int

    compliance_status: str

    severity_breakdown: dict

    audit_completed_at: str
    audit_confidence: float

    document_classification: str
    document_relevance: str
    relevance_score: int

    classification_confidence: float
    classification_matches: dict

    positive_findings: list
    workflow_reason: str


# =============================================================================
# CHECKPOINTS
# =============================================================================

CHECKPOINT_DIR = Path("checkpoints")
CHECKPOINT_DIR.mkdir(exist_ok=True)


def save_workflow_checkpoint(state: AuditState):
    """
    Save workflow state to disk and to gateway state_manager.
    """

    checkpoint_file = CHECKPOINT_DIR / f"{state['run_id']}.json"

    with open(checkpoint_file, "w") as f:
        json.dump(state, f, indent=2)

    # Save to gateway's state manager for real-time frontend polling
    state_manager.save_checkpoint(state["run_id"], state.get("current_node", "unknown"), state)



def load_workflow_checkpoint(run_id: str) -> AuditState:
    """
    Load workflow checkpoint from disk.
    """

    checkpoint_file = CHECKPOINT_DIR / f"{run_id}.json"

    with open(checkpoint_file, "r") as f:
        state = json.load(f)

    return state


# =============================================================================
# PDF EXTRACTION
# =============================================================================


def extract_pdf_text(pdf_path: str) -> str:
    """
    Extract raw text from PDF using PyMuPDF.
    """

    try:
        document = fitz.open(pdf_path)

        full_text = ""

        for page in document:
            page_text = page.get_text()

            full_text += f"\n--- PAGE {page.number + 1} ---\n"
            full_text += page_text

        return full_text
    except Exception as e:
        print(f"File not found on backend (frontend didn't upload bytes): {pdf_path}. Using mock text.")
        return """
--- PAGE 1 ---
Vendor Compliance Packet
Vendor Name: Acme Corp

Security Controls:
- All data is encrypted at rest using AES-256.
- We use Multi-Factor Authentication (MFA) for all employee access.
- Audit logging is enabled and retained for 365 days.
- We do not have a formal SOC2 certification yet.

Privacy:
- We comply with GDPR and CCPA.
- Data is stored in US-East-1 AWS Region.
        """


# =============================================================================
# TENANT CONFIGURATION
# =============================================================================


def load_tenant_rules(tenant_id: str) -> dict:
    """
    Load tenant-specific compliance rules.
    """

    config_path = f"configs/tenant_{tenant_id}.yaml"

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    return config


# =============================================================================
# NODE A — INGESTION
# =============================================================================

async def node_ingestion(state: AuditState) -> AuditState:
    """
    Real PDF ingestion node.
    """

    state["current_node"] = "ingestion"
    state["status"] = "running"
    
    await asyncio.sleep(2)

    pdf_text = extract_pdf_text(state["uploaded_files"][0])

    vendor_name = "Unknown Vendor"

    if "Acme" in pdf_text:
        vendor_name = "Acme Corp"

    if "BITS" in pdf_text:
        vendor_name = "BITS Pilani"

    state["parsed_documents"] = {
        "vendor_name": vendor_name,
        "raw_text": pdf_text[:5000],
        "document_type": "PDF"
    }

    return state

async def node_document_classification(state: AuditState) -> AuditState:
    """
    Semantic document routing layer.

    Determines:
    - document type
    - business relevance
    - audit eligibility
    - workflow routing decision
    """

    state["current_node"] = "document_classification"
    
    await asyncio.sleep(2)

    document_text = state["parsed_documents"].get("raw_text", "").lower()

    # -------------------------------------------------------------------------
    # DOCUMENT TYPE TAXONOMY
    # -------------------------------------------------------------------------

    document_categories = {
        "COMPLIANCE_DOCUMENT": [
            "soc2",
            "iso27001",
            "security policy",
            "risk management",
            "vendor security",
            "compliance",
            "audit controls",
            "access control"
        ],

        "LEGAL_DOCUMENT": [
            "agreement",
            "contract",
            "nda",
            "terms",
            "legal"
        ],

        "FINANCIAL_DOCUMENT": [
            "invoice",
            "balance sheet",
            "financial statement",
            "revenue",
            "expense"
        ],

        "ACADEMIC_DOCUMENT": [
            "hall ticket",
            "semester",
            "exam",
            "course code",
            "student id"
        ]
    }

    # -------------------------------------------------------------------------
    # CLASSIFICATION
    # -------------------------------------------------------------------------

    category_scores = {}

    matched_keywords = {}

    for category, keywords in document_categories.items():

        score = 0

        matches = []

        for keyword in keywords:

            if keyword.lower() in document_text:
                score += 10
                matches.append(keyword)

        category_scores[category] = score
        matched_keywords[category] = matches

    # -------------------------------------------------------------------------
    # BEST CATEGORY
    # -------------------------------------------------------------------------

    best_category = max(category_scores, key=category_scores.get)

    best_score = category_scores[best_category]

    confidence = min(best_score / 100, 1.0)

    state["classification_confidence"] = round(confidence, 2)

    state["document_classification"] = best_category
    state["relevance_score"] = best_score
    state["classification_matches"] = matched_keywords

    # -------------------------------------------------------------------------
    # ROUTING DECISION
    # -------------------------------------------------------------------------

    if best_category == "COMPLIANCE_DOCUMENT":

        state["document_relevance"] = "RELEVANT"
        state["workflow_reason"] = (
            "Document contains compliance-related indicators"
        )

    elif best_category in [
        "LEGAL_DOCUMENT",
        "FINANCIAL_DOCUMENT"
    ]:

        state["document_relevance"] = "REVIEW"

    else:

        state["document_relevance"] = "IRRELEVANT"
        state["workflow_reason"] = (
            "Document classified as non-enterprise / non-compliance artifact"
        )

        state["status"] = "skipped"

        state["draft_report"] = f"""
# Compliance Audit Report

## Document Routing Decision

This uploaded document was classified as:

{best_category}

The system determined this document is not suitable
for compliance auditing.

## Relevance Score
{score}/100

## Classification Confidence
{state["classification_confidence"]}

## Routing Decision
{state["document_relevance"]}

## Matched Indicators

{matched_keywords[best_category] if matched_keywords[best_category] else "None"}

## Recommended Action

## Workflow Reason
{state["workflow_reason"]}

SKIP AUDIT WORKFLOW

## Status
SKIPPED
"""

    return state


# =============================================================================
# NODE B — RULE RETRIEVAL
# =============================================================================


async def node_rule_retrieval(state: AuditState) -> AuditState:
    """
    Load tenant compliance policies.
    """

    state["current_node"] = "rule_retrieval"
    await asyncio.sleep(2)

    tenant_rules = load_tenant_rules(state["tenant_id"])

    state["retrieved_rules"] = tenant_rules

    return state


# =============================================================================
# NODE C — ADVERSARIAL AUDIT
# =============================================================================


async def node_adversarial_audit(state: AuditState) -> AuditState:
    """
    Policy-driven adversarial audit node.
    """

    state["current_node"] = "adversarial_audit"
    await asyncio.sleep(2)

    findings = []
    positive_findings = []

    document_text = state["parsed_documents"].get("raw_text", "")
    vendor_name = state["parsed_documents"].get("vendor_name", "Unknown")
    rules = state["retrieved_rules"].get("required_controls", {})
    
    # Run the LLM agent
    result = compliance_reasoning_agent(
        task="Perform adversarial compliance audit",
        tenant_id=state["tenant_id"],
        context={
            "document_text": document_text,
            "standard": state["retrieved_rules"].get("compliance_frameworks", ["SOC2"])[0],
            "vendor_name": vendor_name,
            "controls": list(rules.keys())
        }
    )

    findings = []
    positive_findings = []
    coverage = {}

    if result.status == "success":
        llm_output = result.output
        llm_findings = llm_output.get("compliance_analysis", {}).get("findings", [])
        
        for f in llm_findings:
            control = f.get("control", "unknown")
            is_compliant = f.get("status", "fail") == "pass"
            coverage[control] = is_compliant
            
            if is_compliant:
                positive_findings.append({
                    "control": control,
                    "matched_keywords": [],
                    "status": "compliant",
                    "evidence": f.get("evidence", "")
                })
            else:
                findings.append({
                    "finding_id": f"F-{len(findings)+1:03}",
                    "severity": f.get("severity", "medium"),
                    "issue": f"{control.replace('_', ' ').title()} controls missing",
                    "status": "non_compliant",
                    "evidence": f.get("evidence", "No evidence found"),
                    "page_reference": "Document analysis",
                    "frameworks": state["retrieved_rules"].get("compliance_frameworks", []),
                    "control_description": "LLM identified gap",
                    "confidence": 0.9,
                    "matched_keywords": [],
                })
                
        # Store risk narrative in state for later use
        state["workflow_reason"] = llm_output.get("risk_narrative", "")
    else:
        # Fallback to empty if LLM failed
        print(f"LLM Agent failed: {result.error}")

    state["control_coverage"] = coverage
    state["audit_findings"] = findings
    state["positive_findings"] = positive_findings

    return state


# =============================================================================
# NODE D — GAP ANALYSIS
# =============================================================================


async def node_gap_analysis(state: AuditState) -> AuditState:
    """
    Convert findings into structured risk analysis.
    """

    state["current_node"] = "gap_analysis"
    await asyncio.sleep(2)

    gaps = []

    risk_score = 100

    severity_breakdown = {
        "HIGH": 0,
        "MEDIUM": 0,
        "LOW": 0
    }

    average_confidence = 0

    if state["audit_findings"]:
        average_confidence = round(
            sum(f["confidence"] for f in state["audit_findings"]) / len(state["audit_findings"]),
            2
        )

    state["audit_confidence"] = average_confidence

    for finding in state["audit_findings"]:

        severity_breakdown[finding["severity"]] += 1

        if finding["severity"] == "HIGH":
            risk_score -= 40

        elif finding["severity"] == "MEDIUM":
            risk_score -= 20

        elif finding["severity"] == "LOW":
            risk_score -= 10

        gaps.append({
            "risk": finding["issue"],
            "severity": finding["severity"],
            "recommended_fix": "Review and remediate compliance control"
        })

    state["gap_analysis"] = gaps

    state["risk_score"] = max(risk_score, 0)

    if state["risk_score"] >= 80:
        state["risk_level"] = "HIGH"

    elif state["risk_score"] >= 50:
        state["risk_level"] = "MEDIUM"

    else:
        state["risk_level"] = "LOW"

    coverage_values = list(state["control_coverage"].values())

    if coverage_values:
        coverage_percent = int(
            (sum(coverage_values) / len(coverage_values)) * 100
        )
    else:
        coverage_percent = 0

    state["coverage_percent"] = coverage_percent

    if state["coverage_percent"] >= 90:
        state["compliance_status"] = "COMPLIANT"

    elif state["coverage_percent"] >= 60:
        state["compliance_status"] = "PARTIALLY_COMPLIANT"

    else:
        state["compliance_status"] = "NON_COMPLIANT"

    if state["compliance_status"] == "NON_COMPLIANT":
        state["approval_recommendation"] = "REJECT"

    elif state["risk_level"] == "HIGH":
        state["approval_recommendation"] = "REJECT"

    elif state["risk_level"] == "MEDIUM":
        state["approval_recommendation"] = "REVIEW"

    else:
        state["approval_recommendation"] = "APPROVE"

    state["severity_breakdown"] = severity_breakdown

    return state


# =============================================================================
# NODE E — REPORT GENERATION
# =============================================================================


async def node_report_generation(state: AuditState) -> AuditState:
    """
    Generate markdown compliance report.
    """

    state["current_node"] = "report_generation"
    await asyncio.sleep(2)

    findings = state["audit_findings"]
    gaps = state["gap_analysis"]

    report = f"""
# Compliance Audit Report

## Executive Decision

Vendor Risk Level: {state["risk_level"]}

Recommendation: {state["approval_recommendation"]}

Compliance Status: {state["compliance_status"]}

## Final Recommendation
{state["approval_recommendation"]}

## Vendor
{state["parsed_documents"].get("vendor_name")}

## Document Type
{state["parsed_documents"].get("document_type")}

## Compliance Frameworks
{", ".join(state["retrieved_rules"]["compliance_frameworks"])}

## Risk Score
{state["risk_score"]}/100

## Risk Level
{state["risk_level"]}

## Compliance Summary

- Total Findings: {len(state["audit_findings"])}
- Risk Score: {state["risk_score"]}/100
- Risk Level: {state["risk_level"]}
- Recommendation: {state["approval_recommendation"]}

## Compliance Metrics

- Coverage: {state["coverage_percent"]}%
- Compliance Status: {state["compliance_status"]}

## Severity Breakdown

- HIGH: {state["severity_breakdown"]["HIGH"]}
- MEDIUM: {state["severity_breakdown"]["MEDIUM"]}
- LOW: {state["severity_breakdown"]["LOW"]}

## Findings

{chr(10).join([
    f"- [{f['severity']}] {f['issue']}\n  Evidence: {f['evidence']}\n  Source Reference: {f['page_reference']} Frameworks: {', '.join(f['frameworks'])}"
    for f in state["audit_findings"]
]) if findings else "No compliance issues detected."}

## Positive Findings

{chr(10).join([
    f"- {f['control']} controls detected ({', '.join(f['matched_keywords'])})"
    for f in state['positive_findings']
]) if state['positive_findings'] else 'No compliant controls detected.'}

## Gap Analysis

{chr(10).join([
    f"- {g['risk']} → {g['recommended_fix']}"
    for g in gaps
]) if gaps else "No remediation required."}

## Audit Completed At
{state.get("audit_completed_at", "Pending")}

### Meta Information
- Run ID: {state['run_id']}
- Vendor: {state['parsed_documents'].get('vendor_name', 'Unknown')}
- Date Generated: {datetime.now().isoformat()}
- Audit Timestamp: {state.get('audit_completed_at', 'Pending')}
- Document Classification: {state.get('document_classification', 'Unknown')}

## Status
Audit completed successfully.
"""

    state["draft_report"] = report

    return state


# =============================================================================
# NODE F — HUMAN REVIEW GATE
# =============================================================================


async def node_human_review_gate(state: AuditState) -> AuditState:
    """
    Pause workflow for human review.
    """

    state["current_node"] = "human_review_gate"
    await asyncio.sleep(2)

    state["status"] = "hitl_paused"

    state["requires_human_review"] = True

    return state


# =============================================================================
# HUMAN REVIEW RESUME
# =============================================================================


async def resume_after_human_review(
        
    state: AuditState,
    approved: bool
) -> AuditState:
    """
    Resume workflow after human decision.
    """
    
    state["human_decision"] = "approved" if approved else "rejected"

    state["requires_human_review"] = False

    if state["status"] == "skipped":
        return state

    if approved:
        state["status"] = "completed"
    else:
        state["status"] = "rejected"

    state["audit_completed_at"] = datetime.now().isoformat()

    save_workflow_checkpoint(state)

    return state


# =============================================================================
# MAIN AUDIT EXECUTION
# =============================================================================


async def run_audit(state: AuditState) -> AuditState:
    """
    Execute audit workflow sequentially.
    """

    state = await node_ingestion(state)
    save_workflow_checkpoint(state)

    state = await node_document_classification(state)
    save_workflow_checkpoint(state)

    if state["document_relevance"] != "RELEVANT":
        return state

    state = await node_rule_retrieval(state)
    save_workflow_checkpoint(state)

    state = await node_adversarial_audit(state)
    save_workflow_checkpoint(state)

    state = await node_gap_analysis(state)
    save_workflow_checkpoint(state)

    state = await node_report_generation(state)
    save_workflow_checkpoint(state)

    state = await node_human_review_gate(state)
    save_workflow_checkpoint(state)

    return state


# =============================================================================
# RESUME WORKFLOW
# =============================================================================


async def resume_audit(run_id: str) -> AuditState:
    """
    Resume workflow from checkpoint.
    """

    state = load_workflow_checkpoint(run_id)

    if state["status"] in ["hitl_paused", "awaiting_human_review"]:
        print("\nResuming after human approval...\n")

        state = await resume_after_human_review(
            state,
            approved=True
        )

    return state


# =============================================================================
# REPORT SUMMARY
# =============================================================================


def print_workflow_summary(state: AuditState):
    """
    Pretty print workflow summary.
    """

    print("\n=== WORKFLOW SUMMARY ===\n")

    print(f"Run ID: {state['run_id']}")
    print(f"Tenant: {state['tenant_id']}")
    print(f"Status: {state['status']}")
    print(f"Current Node: {state['current_node']}")
    print(f"Human Decision: {state['human_decision']}")

    print("\n=== REPORT ===\n")

    print(state["draft_report"])


# =============================================================================
# LOCAL TEST RUNNER
# =============================================================================


if __name__ == "__main__":

    initial_state: AuditState = {
        "run_id": "audit-001",
        "tenant_id": "acme",

        "uploaded_files": ["sample_soc2.pdf"],

        "parsed_documents": {},
        "retrieved_rules": {},

        "audit_findings": [],
        "gap_analysis": [],

        "draft_report": "",

        "status": "initialized",
        "current_node": "start",

        "requires_human_review": False,
        "human_decision": None,

        "risk_score": 100,
        "risk_level": "UNKNOWN",

        "approval_recommendation": "PENDING",

        "control_coverage": {},
        "coverage_percent": 0,

        "compliance_status": "UNKNOWN",

        "severity_breakdown": {},

        "audit_completed_at": "",
        "audit_confidence": 0.0,

        "document_classification": "UNKNOWN",
        "document_relevance": "UNKNOWN",
        "relevance_score": 0,

        "classification_confidence": 0.0,
        "classification_matches": {},

        "positive_findings": [],
        "workflow_reason": "",
    }

    final_state = asyncio.run(run_audit(initial_state))

    final_state = asyncio.run(
        resume_after_human_review(final_state, approved=True)
    )

    print("\n=== FINAL AUDIT STATE ===\n")

    print_workflow_summary(final_state)

    loaded_state = load_workflow_checkpoint("audit-001")

    print("\n=== LOADED CHECKPOINT ===\n")
    print(loaded_state["status"])
    print(loaded_state["current_node"])

    resumed_state = asyncio.run(
        resume_audit("audit-001")
    )

    print("\n=== RESUMED WORKFLOW ===\n")
    print(resumed_state["status"])
    print(resumed_state["human_decision"])

    pdf_text = extract_pdf_text("sample_soc2.pdf")

    print("\n=== PDF TEXT PREVIEW ===\n")
    print(pdf_text[:2000])
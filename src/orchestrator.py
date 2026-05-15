import asyncio
import json
from pathlib import Path
from typing import TypedDict, Optional
from datetime import datetime

import fitz
import yaml


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


# =============================================================================
# CHECKPOINTS
# =============================================================================

CHECKPOINT_DIR = Path("checkpoints")
CHECKPOINT_DIR.mkdir(exist_ok=True)


def save_workflow_checkpoint(state: AuditState):
    """
    Save workflow state to disk.
    """

    checkpoint_file = CHECKPOINT_DIR / f"{state['run_id']}.json"

    with open(checkpoint_file, "w") as f:
        json.dump(state, f, indent=2)



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

    document = fitz.open(pdf_path)

    full_text = ""

    for page in document:
        page_text = page.get_text()

        full_text += f"\n--- PAGE {page.number + 1} ---\n"
        full_text += page_text

    return full_text


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
    state["status"] = "processing"

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


# =============================================================================
# NODE B — RULE RETRIEVAL
# =============================================================================


async def node_rule_retrieval(state: AuditState) -> AuditState:
    """
    Load tenant compliance policies.
    """

    state["current_node"] = "rule_retrieval"

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

    findings = []

    document_text = state["parsed_documents"].get("raw_text", "")

    rules = state["retrieved_rules"]["required_controls"]

    coverage = {
        "encryption": False,
        "mfa": False,
        "audit_logging": False
    }

    # -------------------------------------------------------------------------
    # ENCRYPTION
    # -------------------------------------------------------------------------

    if rules["encryption"]["required"]:
        if "encryption" not in document_text.lower():
            findings.append({
                "severity": rules["encryption"]["severity"],
                "issue": "Missing encryption at rest",
                "status": "non_compliant",
                "evidence": "No encryption-related controls detected in document",
                "page_reference": "Document-wide search",
                "frameworks": state["retrieved_rules"]["compliance_frameworks"]
            })
        else:
            coverage["encryption"] = True

    # -------------------------------------------------------------------------
    # MFA
    # -------------------------------------------------------------------------

    if rules["mfa"]["required"]:
        if "mfa" not in document_text.lower():
            findings.append({
                "severity": rules["mfa"]["severity"],
                "issue": "MFA not enabled",
                "status": "non_compliant",
                "evidence": "No MFA-related controls detected in document",
                "page_reference": "Document-wide search",
                "frameworks": state["retrieved_rules"]["compliance_frameworks"]
            })
        else:
            coverage["mfa"] = True

    # -------------------------------------------------------------------------
    # AUDIT LOGGING
    # -------------------------------------------------------------------------

    if rules["audit_logging"]["required"]:
        if "audit log" not in document_text.lower():
            findings.append({
                "severity": rules["audit_logging"]["severity"],
                "issue": "Audit logging controls missing",
                "status": "non_compliant",
                "evidence": "No audit logging controls detected in document",
                "page_reference": "Document-wide search",
                "frameworks": state["retrieved_rules"]["compliance_frameworks"]
            })
        else:
            coverage["audit_logging"] = True

    state["control_coverage"] = coverage
    state["audit_findings"] = findings

    return state


# =============================================================================
# NODE D — GAP ANALYSIS
# =============================================================================


async def node_gap_analysis(state: AuditState) -> AuditState:
    """
    Convert findings into structured risk analysis.
    """

    state["current_node"] = "gap_analysis"

    gaps = []

    risk_score = 100

    severity_breakdown = {
        "HIGH": 0,
        "MEDIUM": 0,
        "LOW": 0
    }

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
        state["risk_level"] = "LOW"

    elif state["risk_score"] >= 50:
        state["risk_level"] = "MEDIUM"

    else:
        state["risk_level"] = "HIGH"

    if state["risk_level"] == "LOW":
        state["approval_recommendation"] = "APPROVE"

    elif state["risk_level"] == "MEDIUM":
        state["approval_recommendation"] = "REVIEW"

    else:
        state["approval_recommendation"] = "REJECT"

    coverage_values = list(state["control_coverage"].values())

    coverage_percent = int(
        (sum(coverage_values) / len(coverage_values)) * 100
    )

    state["coverage_percent"] = coverage_percent

    if state["coverage_percent"] >= 90:
        state["compliance_status"] = "COMPLIANT"

    elif state["coverage_percent"] >= 60:
        state["compliance_status"] = "PARTIALLY_COMPLIANT"

    else:
        state["compliance_status"] = "NON_COMPLIANT"

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

    findings = state["audit_findings"]
    gaps = state["gap_analysis"]

    report = f"""
# Compliance Audit Report

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

- Total Findings: {len(findings)}
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
    f"- [{f['severity']}] {f['issue']}\n  Evidence: {f['evidence']}\n  Source Reference: {f['page_reference']}"
    for f in findings
]) if findings else "No compliance issues detected."}

## Gap Analysis

{chr(10).join([
    f"- {g['risk']} → {g['recommended_fix']}"
    for g in gaps
]) if gaps else "No remediation required."}

## Audit Completed At
{state["audit_completed_at"]}

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

    state["status"] = "awaiting_human_review"

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

    if state["status"] == "awaiting_human_review":
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

        "audit_completed_at": ""
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
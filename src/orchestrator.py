import uuid
from typing import TypedDict, Optional
import json
from pathlib import Path
# from src.planner import plan_task
# from src.executor import execute_plan
# from src.memory.vector_store import store_memory, search_memory
# from src.memory.state import save_checkpoint
# from src.api.observability import log_event

class AuditState(TypedDict):
    run_id: str
    tenant_id: str

    uploaded_files: list[str]

    parsed_documents: dict
    retrieved_rules: dict

    audit_findings: dict
    gap_analysis: dict

    draft_report: str

    status: str
    current_node: str

    requires_human_review: bool
    human_decision: Optional[str]

CHECKPOINT_DIR = Path("checkpoints")
CHECKPOINT_DIR.mkdir(exist_ok=True)


def save_workflow_checkpoint(state: AuditState):
    """
    Saves workflow state to disk after each node.
    """

    checkpoint_file = CHECKPOINT_DIR / f"{state['run_id']}.json"

    with open(checkpoint_file, "w") as f:
        json.dump(state, f, indent=2)

def load_workflow_checkpoint(run_id: str) -> AuditState:
    """
    Loads workflow state from disk.
    """

    checkpoint_file = CHECKPOINT_DIR / f"{run_id}.json"

    with open(checkpoint_file, "r") as f:
        state = json.load(f)

    return state

async def resume_audit(run_id: str) -> AuditState:
    """
    Resume workflow execution from saved checkpoint.
    """

    state = load_workflow_checkpoint(run_id)

    if state["status"] == "awaiting_human_review":
        print("\nResuming after human approval...\n")

        state = await resume_after_human_review(
            state,
            approved=True
        )

    return state

async def execute(run_id: str, payload: dict):
    task = payload.get("task")

    log_event(run_id, "orchestrator_started", {
        "task": task
    })

    # Step 1: Retrieve previous memory
    previous_context = search_memory(task)

    log_event(run_id, "memory_retrieved", {
        "context": previous_context
    })

    # Step 2: Create plan
    plan = plan_task(task, previous_context)

    log_event(run_id, "plan_created", {
        "plan": plan
    })

    # Step 3: Execute plan
    result = execute_plan(plan)

    log_event(run_id, "execution_completed", {
        "result": result
    })

    # Step 4: Store new memory
    store_memory(
        text=f"Task: {task}\nResult: {result}"
    )

    log_event(run_id, "memory_stored", {})

    # Step 5: Save checkpoint
    save_checkpoint(run_id, {
        "task": task,
        "plan": plan,
        "result": result
    })

    log_event(run_id, "checkpoint_saved", {})

    return {
        "run_id": run_id,
        "status": "completed",
        "task": task,
        "plan": plan,
        "result": result,
        "previous_context": previous_context
    }

async def node_ingestion(state: AuditState) -> AuditState:
    """
    Simulates document ingestion/parsing.
    Later this will call OCR/document tools.
    """

    state["current_node"] = "ingestion"
    state["status"] = "processing"

    # Temporary mock parsing
    state["parsed_documents"] = {
        "vendor_name": "Acme Corp",
        "document_type": "SOC2",
        "controls_found": [
            "Encryption at Rest",
            "MFA Enabled",
            "Access Logging"
        ]
    }

    return state

async def node_rule_retrieval(state: AuditState) -> AuditState:
    """
    Simulates retrieval of compliance rules
    for a specific tenant/client.
    """

    state["current_node"] = "rule_retrieval"

    # Temporary mock rules
    state["retrieved_rules"] = {
        "encryption_required": True,
        "mfa_required": True,
        "soc2_required": True,
        "audit_log_retention_days": 90
    }

    return state

async def node_adversarial_audit(state: AuditState) -> AuditState:
    """
    Simulates adversarial compliance auditing.
    Looks for reasons to reject compliance.
    """

    state["current_node"] = "adversarial_audit"

    findings = []

    controls = state["parsed_documents"].get("controls_found", [])

    if "Encryption at Rest" not in controls:
        findings.append({
            "severity": "HIGH",
            "issue": "Missing encryption at rest",
            "status": "non_compliant"
        })

    if "MFA Enabled" not in controls:
        findings.append({
            "severity": "MEDIUM",
            "issue": "MFA not enabled",
            "status": "non_compliant"
        })

    state["audit_findings"] = findings

    return state

async def node_gap_analysis(state: AuditState) -> AuditState:
    """
    Converts raw audit findings into
    structured mitigation guidance.
    """

    state["current_node"] = "gap_analysis"

    gaps = []

    for finding in state["audit_findings"]:
        gaps.append({
            "risk": finding["issue"],
            "severity": finding["severity"],
            "recommended_fix": "Review and remediate compliance control"
        })

    state["gap_analysis"] = gaps

    return state

async def node_report_generation(state: AuditState) -> AuditState:
    """
    Generates a draft markdown audit report.
    """

    state["current_node"] = "report_generation"

    findings = state["audit_findings"]
    gaps = state["gap_analysis"]

    report = f"""
# Compliance Audit Report

## Vendor
{state["parsed_documents"].get("vendor_name")}

## Document Type
{state["parsed_documents"].get("document_type")}

## Findings
Total Findings: {len(findings)}

## Gap Analysis
Total Gaps: {len(gaps)}

## Status
Audit completed successfully.
"""

    state["draft_report"] = report

    return state

async def node_human_review_gate(state: AuditState) -> AuditState:
    """
    Simulates a Human-in-the-Loop pause gate.
    """

    state["current_node"] = "human_review_gate"

    state["status"] = "awaiting_human_review"

    state["requires_human_review"] = True

    return state

async def resume_after_human_review(
    state: AuditState,
    approved: bool
) -> AuditState:
    """
    Simulates human approval/rejection.
    """

    state["human_decision"] = "approved" if approved else "rejected"

    state["requires_human_review"] = False

    if approved:
        state["status"] = "completed"
    else:
        state["status"] = "rejected"

    save_workflow_checkpoint(state)
    return state

async def run_audit(state: AuditState) -> AuditState:
    """
    Main audit workflow runner.
    Executes nodes sequentially.
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

def print_workflow_summary(state: AuditState):
    """
    Prints a readable workflow summary.
    """

    print("\n=== WORKFLOW SUMMARY ===\n")

    print(f"Run ID: {state['run_id']}")
    print(f"Tenant: {state['tenant_id']}")
    print(f"Status: {state['status']}")
    print(f"Current Node: {state['current_node']}")
    print(f"Human Decision: {state['human_decision']}")

    print("\n=== REPORT ===\n")

    print(state["draft_report"])

if __name__ == "__main__":
    import asyncio

    initial_state: AuditState = {
        "run_id": "audit-001",
        "tenant_id": "acme",

        "uploaded_files": ["sample_soc2.pdf"],

        "parsed_documents": {},
        "retrieved_rules": {},

        "audit_findings": {},
        "gap_analysis": {},

        "draft_report": "",

        "status": "initialized",
        "current_node": "start",

        "requires_human_review": False,
        "human_decision": None
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
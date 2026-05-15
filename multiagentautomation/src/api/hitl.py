"""
HITL API — FastAPI router mounted at /hitl
Part of Phase 3: Memory, State & Governance.

Endpoints
---------
POST /hitl/approve/{run_id}    — approve + resume a paused audit
POST /hitl/reject/{run_id}     — reject a paused audit
GET  /hitl/pending             — list all unresolved HITL audits
GET  /hitl/status/{run_id}     — full task + checkpoint + hitl snapshot
GET  /hitl/checkpoints/{run_id}— all saved checkpoints for an audit trail

All responses are JSON. 4xx errors are returned as {"detail": "..."}.
"""

from __future__ import annotations

import json
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from src.memory.state import StateManager, TaskStatus
from src.memory.trace import TraceLogger

router = APIRouter(prefix="/hitl", tags=["HITL"])

# Initialize the global state manager instance (for MVP this is fine. 
# For production, you might inject this via FastAPI Depends)
state_manager = StateManager()


# ── request / response models ─────────────────────────────────────────────────

class ApproveRequest(BaseModel):
    approved_by: str = Field(..., description="Username or system ID approving the audit (e.g., 'admin_1')")
    feedback: Optional[str] = Field(None, description="Optional note to append to the audit trail")

class RejectRequest(BaseModel):
    rejected_by: str = Field(..., description="Username or system ID rejecting the audit")
    reason: str = Field(..., description="Mandatory reason for rejection (fed back to TraceLogger)")


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.post("/approve/{run_id}", summary="Approve and resume a HITL-paused audit")
async def approve(run_id: str, body: ApproveRequest):
    """
    Approve an audit that is currently flagged as **hitl_paused**.
    Transitions: hitl_paused → running (resumes orchestrator)
    """
    summary = state_manager.get_full_state_summary(run_id)
    
    if "error" in summary:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
        
    if summary.get("status") != TaskStatus.HITL_PAUSED.value:
        raise HTTPException(
            status_code=409,
            detail=f"Run '{run_id}' is currently '{summary.get('status')}', not 'hitl_paused'."
        )

    try:
        new_state = await state_manager.resume_workflow(
            run_id=run_id,
            decision=TaskStatus.APPROVED,
            feedback=body.feedback
        )
        
        # Log the specific HITL resolution dynamically
        logger = TraceLogger(component="api.hitl", run_id=run_id)
        logger.log_approval(
            approved_by=body.approved_by, 
            action="approve", 
            feedback=body.feedback
        )

        # TODO (Phase 1): Trigger Orchestrator wake-up event here or via message queue
        
    except Exception as exc:
        logger = TraceLogger(component="api.hitl", run_id=run_id)
        logger.log_error(message="Failed to approve task", error=exc)
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "status": "approved",
        "run_id": run_id,
        "current_node": summary.get("current_node")
    }


@router.post("/reject/{run_id}", summary="Reject a HITL-paused audit")
async def reject(run_id: str, body: RejectRequest):
    """
    Reject an audit in **hitl_paused** state due to critical compliance failure.
    Transitions: hitl_paused → failed
    """
    summary = state_manager.get_full_state_summary(run_id)
    
    if "error" in summary:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
        
    if summary.get("status") != TaskStatus.HITL_PAUSED.value:
        raise HTTPException(
            status_code=409,
            detail=f"Run '{run_id}' is currently '{summary.get('status')}', not 'hitl_paused'."
        )

    try:
        new_state = await state_manager.resume_workflow(
            run_id=run_id,
            decision=TaskStatus.REJECTED,
            feedback=body.reason
        )

        logger = TraceLogger(component="api.hitl", run_id=run_id)
        logger.log_state_transition(
            from_state=TaskStatus.HITL_PAUSED.value,
            to_state=TaskStatus.FAILED.value,
            node_id=summary.get("current_node", "unknown")
        )

    except Exception as exc:
        logger = TraceLogger(component="api.hitl", run_id=run_id)
        logger.log_error(message="Failed to reject task", error=exc)
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "status": "rejected",
        "run_id": run_id,
        "reason": body.reason
    }


@router.get("/pending", summary="List all audits awaiting human review")
def pending():
    """Return every unresolved HITL record across all clients."""
    records = state_manager.list_active_hitl()
    return {"count": len(records), "tasks": records}


@router.get("/status/{run_id}", summary="Full snapshot of audit + HITL state")
def status(run_id: str):
    """
    Returns a combined view for your dashboard:
    - current task state 
    - active HITL reason (why the Judge flagged it)
    - latest checkpoint payload
    """
    summary = state_manager.get_full_state_summary(run_id)
    if "error" in summary:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
        
    return summary


@router.get("/checkpoints/{run_id}", summary="All saved checkpoints for an audit trail")
def checkpoints(run_id: str):
    """
    Retrieves the entire history of an audit. 
    Crucial for generating the final compliance evidence report.
    """
    history = []
    # Glob through the checkpoint directory for all files belonging to this run
    files = sorted(state_manager.checkpoint_dir.glob(f"{run_id}_*.json"))
    
    if not files:
        raise HTTPException(status_code=404, detail=f"No checkpoints found for run '{run_id}'")

    for file_path in files:
        try:
            with open(file_path, 'r') as f:
                history.append(json.load(f))
        except Exception:
            continue

    return {
        "run_id": run_id,
        "count": len(history),
        "audit_trail": history
    }
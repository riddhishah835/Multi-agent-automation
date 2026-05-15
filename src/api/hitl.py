"""
HITL API — FastAPI router mounted at /hitl

Endpoints
---------
POST /hitl/approve/{task_id}    — approve + resume a paused task
POST /hitl/reject/{task_id}     — reject a paused task
GET  /hitl/pending              — list all unresolved HITL tasks
GET  /hitl/status/{task_id}     — full task + checkpoint + hitl snapshot
GET  /hitl/checkpoints/{task_id}— all saved checkpoints for a task

All responses are JSON.  4xx errors are returned as {"detail": "..."}.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.memory.state import (
    approve_task,
    get_hitl_record,
    get_task,
    list_pending_hitl,
    load_checkpoints,
    reject_task,
    resume_context,
)
from src.memory.trace import TraceLogger

router = APIRouter(prefix="/hitl", tags=["HITL"])
logger = TraceLogger(component="api.hitl")


# ── request / response models ─────────────────────────────────────────────────

class ApproveRequest(BaseModel):
    approved_by: str  = Field(..., description="Username or system ID approving the task")
    resume_action: str = Field("continue", description="continue | retry | skip")


class RejectRequest(BaseModel):
    rejected_by: str  = Field(..., description="Username or system ID rejecting the task")
    reason:      str  = Field("", description="Human-readable rejection reason")


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.post("/approve/{task_id}", summary="Approve and resume a HITL-paused task")
def approve(task_id: str, body: ApproveRequest):
    """
    Approve a task that is currently in **hitl_paused** state.

    Transitions: hitl_paused → approved → (orchestrator picks up from checkpoint)
    """
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")
    if task["state"] != "hitl_paused":
        raise HTTPException(
            status_code=409,
            detail=(
                f"Task '{task_id}' is in state '{task['state']}', "
                "not 'hitl_paused'. Cannot approve."
            ),
        )

    try:
        result = approve_task(
            task_id=task_id,
            approved_by=body.approved_by,
            resume_action=body.resume_action,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.log_event(event="approve_error", task_id=task_id, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "status":  "approved",
        "task_id": task_id,
        **result,
    }


@router.post("/reject/{task_id}", summary="Reject a HITL-paused task")
def reject(task_id: str, body: RejectRequest):
    """
    Reject a task in **hitl_paused** state.

    Transitions: hitl_paused → rejected → failed
    """
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")
    if task["state"] != "hitl_paused":
        raise HTTPException(
            status_code=409,
            detail=(
                f"Task '{task_id}' is in state '{task['state']}', "
                "not 'hitl_paused'. Cannot reject."
            ),
        )

    try:
        result = reject_task(
            task_id=task_id,
            rejected_by=body.rejected_by,
            reason=body.reason,
        )
    except Exception as exc:
        logger.log_event(event="reject_error", task_id=task_id, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "status":  "rejected",
        "task_id": task_id,
        **result,
    }


@router.get("/pending", summary="List all tasks awaiting human review")
def pending():
    """Return every unresolved HITL record across all tasks."""
    records = list_pending_hitl()
    return {"count": len(records), "tasks": records}


@router.get("/status/{task_id}", summary="Full snapshot of task + HITL + latest checkpoint")
def status(task_id: str):
    """
    Returns a combined view useful for the human reviewer:
    - current task state and history
    - active HITL record (reason, context, who flagged it)
    - latest checkpoint so the reviewer knows where execution paused
    """
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")

    ctx = resume_context(task_id)
    return {
        "task_id":     task_id,
        "state":       task["state"],
        "task":        ctx["task"],
        "hitl":        ctx["hitl"],
        "checkpoint":  ctx["checkpoint"],
    }


@router.get("/checkpoints/{task_id}", summary="All saved checkpoints for a task")
def checkpoints(task_id: str):
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")

    chkpts = load_checkpoints(task_id)
    return {"task_id": task_id, "count": len(chkpts), "checkpoints": chkpts}
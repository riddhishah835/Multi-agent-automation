"""
Agentic OS Gateway - API Layer
Handles request routing, authentication, and task execution
"""

from fastapi import FastAPI, HTTPException, Depends, Header, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import logging
import asyncio
import uuid
from datetime import datetime
import json
from enum import Enum

# Import our modules
from src.config_loader import ConfigLoader, get_tenant_config, get_config_loader
from src.observability import ObservabilityTracker
from src.memory.state import StateManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# Initialize Core Components
# ============================================================================

config_loader = get_config_loader("configs")
observability = ObservabilityTracker("agentic_os")
state_manager = StateManager("checkpoints")

# Create FastAPI app
app = FastAPI(
    title="Agentic OS Gateway",
    description="API Gateway for Multi-Tenant Agentic OS",
    version="1.0.0"
)

# ============================================================================
# Request/Response Models
# ============================================================================

class TaskStatus(str, Enum):
    """Task status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    APPROVED = "approved"
    COMPLETED = "completed"
    FAILED = "failed"


class SubmitTaskRequest(BaseModel):
    """Request model for task submission"""
    task: str
    workflow_id: str = "default"
    priority: int = 1
    metadata: Dict[str, Any] = {}


class TaskStatusResponse(BaseModel):
    """Response model for task status"""
    run_id: str
    status: TaskStatus
    progress: float
    message: str
    needs_approval: bool = False
    result: Optional[Dict[str, Any]] = None


class ApprovalRequest(BaseModel):
    """Request model for approval"""
    approved: bool
    reason: Optional[str] = None
    approver_id: str = "system"


class HealthCheckResponse(BaseModel):
    """Response model for health check"""
    status: str
    timestamp: str
    components: Dict[str, str]
    version: str


# ============================================================================
# Authentication & Validation
# ============================================================================

def extract_tenant_id(authorization: Optional[str] = Header(None)) -> str:
    """
    Extract tenant ID from Authorization header
    Format: "Bearer tenant_<tenant_id>"
    
    Args:
        authorization: Authorization header value
        
    Returns:
        Tenant ID
        
    Raises:
        HTTPException: If authorization is invalid
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")
    
    token = authorization.replace("Bearer ", "")
    
    # Simple token parsing: Bearer tenant_<tenant_id>
    if not token.startswith("tenant_"):
        raise HTTPException(status_code=401, detail="Invalid token format")
    
    tenant_id = token.replace("tenant_", "")
    
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Missing tenant ID")
    
    return tenant_id


def validate_tenant(tenant_id: str) -> bool:
    """
    Validate that tenant exists and is authorized
    
    Args:
        tenant_id: The tenant ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    return config_loader.validate_tenant(tenant_id)


# ============================================================================
# API Endpoints
# ============================================================================

@app.post("/submit", response_model=Dict[str, Any])
async def submit_task(
    request: SubmitTaskRequest,
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Submit a new task for execution
    
    Request Format:
    ```
    POST /submit
    Authorization: Bearer tenant_acme_v1
    Content-Type: application/json
    
    {
        "task": "Find top 5 AI companies",
        "workflow_id": "default",
        "priority": 1,
        "metadata": {"source": "dashboard"}
    }
    ```
    
    Returns:
    ```json
    {
        "run_id": "run_abc123xyz",
        "status": "pending",
        "message": "Task submitted successfully",
        "workflow_id": "default"
    }
    ```
    """
    trace_id = str(uuid.uuid4())
    logger.info(f"[{trace_id}] Submit task request received")
    
    try:
        # Extract and validate tenant
        tenant_id = extract_tenant_id(authorization)
        
        if not validate_tenant(tenant_id):
            logger.warning(f"[{trace_id}] Invalid tenant: {tenant_id}")
            raise HTTPException(status_code=403, detail="Invalid tenant")
        
        # Validate request
        if not request.task or len(request.task.strip()) == 0:
            raise HTTPException(status_code=400, detail="Task cannot be empty")
        
        # Generate run ID
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        
        # Create initial state
        initial_state = {
            "run_id": run_id,
            "tenant_id": tenant_id,
            "task": request.task,
            "workflow_id": request.workflow_id,
            "status": "pending",
            "priority": request.priority,
            "metadata": request.metadata,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "progress": 0.0,
            "trace_id": trace_id
        }
        
        # Save initial state
        state_manager.save_checkpoint(run_id, "gateway", initial_state)
        
        # Start observability tracking
        # observability.start_trace(trace_id, {
        #     "run_id": run_id,
        #     "tenant_id": tenant_id,
        #     "task_type": "task_submission"
        # })
        
        # Queue async execution (you'll connect this to P1's orchestrator)
        # For now, we just update status to running
        background_tasks.add_task(execute_task_async, run_id, initial_state, trace_id)
        
        logger.info(f"[{trace_id}] Task submitted successfully: {run_id}")
        
        return {
            "run_id": run_id,
            "status": "pending",
            "message": "Task submitted successfully",
            "workflow_id": request.workflow_id,
            "tenant_id": tenant_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{trace_id}] Error submitting task: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/status/{run_id}", response_model=TaskStatusResponse)
async def get_status(
    run_id: str,
    authorization: Optional[str] = Header(None)
) -> TaskStatusResponse:
    """
    Get the status of a submitted task
    
    Request Format:
    ```
    GET /status/run_abc123xyz
    Authorization: Bearer tenant_acme_v1
    ```
    
    Returns:
    ```json
    {
        "run_id": "run_abc123xyz",
        "status": "running",
        "progress": 45.5,
        "message": "Processing task...",
        "needs_approval": false,
        "result": null
    }
    ```
    """
    trace_id = str(uuid.uuid4())
    logger.info(f"[{trace_id}] Status check for run: {run_id}")
    
    try:
        # Extract and validate tenant
        tenant_id = extract_tenant_id(authorization)
        
        # Load state
        checkpoint = state_manager.load_checkpoint(run_id)
        state = checkpoint["state"] if checkpoint else None
        
        if not state:
            logger.warning(f"[{trace_id}] Run not found: {run_id}")
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        
        # Verify tenant ownership
        if state.get("tenant_id") != tenant_id:
            logger.warning(f"[{trace_id}] Tenant mismatch for run: {run_id}")
            raise HTTPException(status_code=403, detail="Unauthorized")
        
        # Create response
        response = TaskStatusResponse(
            run_id=run_id,
            status=TaskStatus(state.get("status", "pending")),
            progress=state.get("progress", 0.0),
            message=state.get("message", ""),
            needs_approval=state.get("needs_approval", False),
            result=state.get("result")
        )
        
        logger.info(f"[{trace_id}] Status returned: {response.status}")
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{trace_id}] Error getting status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/approve/{run_id}", response_model=Dict[str, Any])
async def approve_task(
    run_id: str,
    approval: ApprovalRequest,
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Approve or reject a task waiting for approval
    
    Request Format:
    ```
    POST /approve/run_abc123xyz
    Authorization: Bearer tenant_acme_v1
    Content-Type: application/json
    
    {
        "approved": true,
        "reason": "Looks good",
        "approver_id": "user_123"
    }
    ```
    
    Returns:
    ```json
    {
        "run_id": "run_abc123xyz",
        "status": "approved",
        "message": "Task approved and resumed"
    }
    ```
    """
    trace_id = str(uuid.uuid4())
    logger.info(f"[{trace_id}] Approval request for run: {run_id}")
    
    try:
        # Extract and validate tenant
        tenant_id = extract_tenant_id(authorization)
        
        # Load state
        checkpoint = state_manager.load_checkpoint(run_id,"gateway")
        state = checkpoint["state"] if checkpoint else None
        
        if not state:
            logger.warning(f"[{trace_id}] Run not found: {run_id}")
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        
        # Verify tenant ownership
        if state.get("tenant_id") != tenant_id:
            logger.warning(f"[{trace_id}] Tenant mismatch for run: {run_id}")
            raise HTTPException(status_code=403, detail="Unauthorized")
        
        # Verify task is waiting for approval
        if state.get("status") != "waiting_approval":
            raise HTTPException(
                status_code=400,
                detail=f"Task is not waiting for approval (current status: {state.get('status')})"
            )
        
        # Update state with approval
        state["approval"] = {
            "approved": approval.approved,
            "reason": approval.reason,
            "approver_id": approval.approver_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Update status based on approval
        if approval.approved:
            state["status"] = "approved"
            state["message"] = "Task approved and resumed"
            # Queue resumption (you'll connect this to P1's orchestrator)
            background_tasks.add_task(resume_task_async, run_id, state, trace_id)
        else:
            state["status"] = "failed"
            state["message"] = f"Task rejected: {approval.reason}"
        
        state["updated_at"] = datetime.utcnow().isoformat()
        state_manager.save_checkpoint(run_id, "gateway", state)
        
        logger.info(f"[{trace_id}] Approval processed: {approval.approved}")
        
        return {
            "run_id": run_id,
            "status": state["status"],
            "message": state["message"],
            "approval": state["approval"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{trace_id}] Error processing approval: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """
    Check the health of the system
    
    Request Format:
    ```
    GET /health
    ```
    
    Returns:
    ```json
    {
        "status": "healthy",
        "timestamp": "2026-05-15T10:30:00Z",
        "components": {
            "api": "healthy",
            "state_manager": "healthy",
            "config_loader": "healthy",
            "observability": "healthy"
        },
        "version": "1.0.0"
    }
    ```
    """
    logger.info("Health check requested")
    
    components = {
        "api": "healthy",
        "state_manager": "healthy",
        "config_loader": "healthy",
        "observability": "healthy"
    }
    
    # Verify state manager can write
    try:
        test_id = f"test_{uuid.uuid4().hex[:8]}"
        test_state = {"test": True, "timestamp": datetime.utcnow().isoformat()}
        state_manager.save_checkpoint(test_id, "healthcheck", test_state)
        # state_manager.delete_state(test_id)
    except Exception as e:
        logger.warning(f"State manager health check failed: {e}")
        components["state_manager"] = "degraded"
    
    # Verify config loader can load
    try:
        config_loader.list_tenants()
    except Exception as e:
        logger.warning(f"Config loader health check failed: {e}")
        components["config_loader"] = "degraded"
    
    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        components=components,
        version="1.0.0"
    )


# ============================================================================
# Background Tasks
# ============================================================================

async def execute_task_async(run_id: str, state: Dict[str, Any], trace_id: str) -> None:
    """
    Asynchronously execute a task
    
    This is where you'll integrate with P1's orchestrator.
    For now, it simulates execution.
    
    Args:
        run_id: The run ID
        state: The task state
        trace_id: The trace ID for observability
    """
    logger.info(f"[{trace_id}] Starting async execution for {run_id}")
    
    try:
        # TODO: INTEGRATION POINT FOR P1
        # Replace this with actual call to P1's orchestrator
        # from src.orchestrator import execute_dag
        # result = await execute_dag(state)
        
        # Simulate execution
        state["status"] = "running"
        state["progress"] = 25.0
        state["message"] = "Executing task..."
        state["updated_at"] = datetime.utcnow().isoformat()
        state_manager.save_checkpoint(run_id, "gateway", state)
        
        await asyncio.sleep(2)
        
        state["progress"] = 50.0
        state_manager.save_checkpoint(run_id, "gateway", state)
        
        await asyncio.sleep(2)
        
        # Simulate completion
        state["status"] = "completed"
        state["progress"] = 100.0
        state["message"] = "Task completed successfully"
        state["result"] = {
            "output": f"Processed task: {state['task']}",
            "tokens_used": 1234,
            "cost": 0.05
        }
        state["updated_at"] = datetime.utcnow().isoformat()
        state_manager.save_checkpoint(run_id, "gateway", state)
        
        # Record in observability
        # observability.end_trace(trace_id, {
        #     "status": "success",
        #     "tokens": 1234,
        #     "cost": 0.05
        # })
        
        logger.info(f"[{trace_id}] Task execution completed: {run_id}")
    
    except Exception as e:
        logger.error(f"[{trace_id}] Task execution failed: {str(e)}", exc_info=True)
        
        state["status"] = "failed"
        state["message"] = f"Execution failed: {str(e)}"
        state["updated_at"] = datetime.utcnow().isoformat()
        state_manager.save_checkpoint(run_id, "gateway", state)
        
        observability.end_trace(trace_id, {
            "status": "error",
            "error": str(e)
        })


async def resume_task_async(run_id: str, state: Dict[str, Any], trace_id: str) -> None:
    """
    Asynchronously resume a task after approval
    
    This is where you'll integrate with P1's orchestrator to resume.
    For now, it simulates resumption.
    
    Args:
        run_id: The run ID
        state: The task state
        trace_id: The trace ID for observability
    """
    logger.info(f"[{trace_id}] Resuming task after approval: {run_id}")
    
    try:
        # TODO: INTEGRATION POINT FOR P1
        # Resume execution with the approved state
        
        # Simulate resumption
        state["status"] = "running"
        state["progress"] = 75.0
        state["message"] = "Resuming after approval..."
        state["updated_at"] = datetime.utcnow().isoformat()
        state_manager.save_checkpoint(run_id, "gateway", state)
        
        await asyncio.sleep(1)
        
        state["status"] = "completed"
        state["progress"] = 100.0
        state["message"] = "Task completed successfully"
        state["result"] = {
            "output": f"Completed task after approval: {state['task']}",
            "tokens_used": 5678,
            "cost": 0.10
        }
        state["updated_at"] = datetime.utcnow().isoformat()
        state_manager.save_checkpoint(run_id, "gateway", state)
        
        # observability.end_trace(trace_id, {
        #     "status": "success",
        #     "tokens": 5678,
        #     "cost": 0.10
        # })
        
        logger.info(f"[{trace_id}] Task resumed and completed: {run_id}")
    
    except Exception as e:
        logger.error(f"[{trace_id}] Task resumption failed: {str(e)}", exc_info=True)
        
        state["status"] = "failed"
        state["message"] = f"Resumption failed: {str(e)}"
        state["updated_at"] = datetime.utcnow().isoformat()
        state_manager.save_checkpoint(run_id, "gateway", state)
        
        # observability.end_trace(trace_id, {
        #     "status": "error",
        #     "error": str(e)
        # })


# ============================================================================
# Startup/Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("=" * 80)
    logger.info("Agentic OS Gateway Starting")
    logger.info("=" * 80)
    
    # Verify configuration
    tenants = config_loader.list_tenants()
    logger.info(f"Loaded {len(tenants)} tenant(s): {tenants}")
    
    # Verify state manager
    logger.info("State manager initialized")
    
    # Verify observability
    logger.info("Observability manager initialized")
    
    logger.info("=" * 80)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("=" * 80)
    logger.info("Agentic OS Gateway Shutting Down")
    logger.info("=" * 80)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )

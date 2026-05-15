"""
API Gateway for Agentic OS
Handles: Task submission, status tracking, approval requests, health checks
"""

from fastapi import FastAPI, HTTPException, Depends, Header, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
import logging
from datetime import datetime
import json

# Import internal modules (will be available after P1, P2, P3 complete)
from src.config_loader import ConfigLoader, get_tenant_config
from src.observability import ObservabilityTracker, log_trace
from src.memory.state import StateManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# PYDANTIC SCHEMAS FOR REQUEST/RESPONSE
# ============================================================================

class TaskSubmission(BaseModel):
    """Input schema for task submission"""
    task: str  # User's natural language request
    workflow_id: Optional[str] = "default"
    metadata: Optional[Dict[str, Any]] = None


class TaskStatusResponse(BaseModel):
    """Response schema for task status"""
    run_id: str
    status: str  # "submitted", "processing", "awaiting_approval", "completed", "failed"
    progress: Optional[str] = None
    current_node: Optional[str] = None
    requires_approval: bool = False
    approval_url: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ApprovalRequest(BaseModel):
    """Request schema for approval endpoint"""
    approved: bool
    reason: Optional[str] = None
    notes: Optional[str] = None


class ApprovalResponse(BaseModel):
    """Response schema for approval"""
    run_id: str
    status: str
    message: str
    approved_at: datetime


class HealthCheckResponse(BaseModel):
    """Response schema for health check"""
    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: datetime
    components: Dict[str, str]
    version: str = "1.0.0"


# ============================================================================
# DEPENDENCY INJECTION & AUTH
# ============================================================================

def get_tenant_id_from_token(authorization: str = Header(None)) -> str:
    """
    Extract tenant_id from JWT token in Authorization header.
    Format: "Bearer <jwt_token>"
    
    For demo purposes, we'll accept a simple "Bearer tenant_acme" format.
    In production, decode the JWT properly.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    try:
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise ValueError("Invalid authorization header format")
        
        token = parts[1]
        
        # DEMO MODE: For development, extract tenant from token directly
        # In production, use PyJWT to decode and validate signature
        if token.startswith("tenant_"):
            tenant_id = token.split("_")[1].split("_")[0]  # Extract "acme" from "tenant_acme_v1"
            return tenant_id
        
        # Fallback: Extract from token claims (production approach)
        # from jose import jwt
        # claims = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        # return claims.get("tenant_id")
        
        raise ValueError("Could not extract tenant_id from token")
    
    except Exception as e:
        logger.error(f"Auth error: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token")


# ============================================================================
# FASTAPI APP INITIALIZATION
# ============================================================================

app = FastAPI(
    title="Agentic OS Gateway",
    description="Multi-tenant orchestration platform for AI agents",
    version="1.0.0"
)

# Add CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize core services
config_loader = ConfigLoader()
observability = ObservabilityTracker()
state_manager = StateManager()

# In-memory task store (for demo; replace with database in production)
tasks_store: Dict[str, Dict[str, Any]] = {}


# ============================================================================
# ENDPOINT 1: HEALTH CHECK
# ============================================================================

@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Check system health and component status.
    Called by load balancers and monitoring systems.
    """
    try:
        # Check each component's availability
        components = {
            "api": "healthy",
            "orchestrator": "healthy",  # Will be checked against P1
            "redis_cache": "degraded",  # Check Redis connection
            "vector_db": "degraded",    # Check FAISS/Qdrant
            "config_loader": "healthy"
        }
        
        # Try to connect to Redis (basic check)
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, socket_connect_timeout=2)
            r.ping()
            components["redis_cache"] = "healthy"
        except Exception as e:
            logger.warning(f"Redis health check failed: {str(e)}")
        
        # Overall status
        if all(v == "healthy" for v in components.values()):
            status = "healthy"
        elif any(v == "healthy" for v in components.values()):
            status = "degraded"
        else:
            status = "unhealthy"
        
        return HealthCheckResponse(
            status=status,
            timestamp=datetime.now(),
            components=components
        )
    
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return HealthCheckResponse(
            status="unhealthy",
            timestamp=datetime.now(),
            components={"error": str(e)}
        )


# ============================================================================
# ENDPOINT 2: SUBMIT TASK
# ============================================================================

@app.post("/submit", response_model=TaskStatusResponse)
async def submit_task(
    submission: TaskSubmission,
    tenant_id: str = Depends(get_tenant_id_from_token),
    background_tasks: BackgroundTasks = None
):
    """
    Submit a new task for processing.
    
    Flow:
    1. Extract tenant_id from auth token
    2. Load tenant-specific configuration
    3. Validate task against tenant's allowed workflows
    4. Create run_id and initial state
    5. Queue task for async orchestration (via P1)
    6. Return task ID for polling
    """
    try:
        # Generate unique run ID
        run_id = str(uuid.uuid4())
        
        # Load tenant configuration
        tenant_config = config_loader.load_tenant_config(tenant_id)
        if not tenant_config:
            raise HTTPException(status_code=403, detail=f"Tenant '{tenant_id}' not found")
        
        # Validate workflow is enabled for this tenant
        if submission.workflow_id not in tenant_config.get("enabled_workflows", ["default"]):
            raise HTTPException(
                status_code=403,
                detail=f"Workflow '{submission.workflow_id}' not enabled for tenant '{tenant_id}'"
            )
        
        # Create initial state
        initial_state = {
            "run_id": run_id,
            "tenant_id": tenant_id,
            "original_request": submission.task,
            "workflow_id": submission.workflow_id,
            "metadata": submission.metadata or {},
            "tenant_config": tenant_config,
            "current_plan": [],
            "gathered_context": "",
            "final_output": "",
            "requires_human_approval": False,
            "status": "submitted",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Store task in memory (will be replaced with database)
        tasks_store[run_id] = initial_state
        
        # Log submission event
        observability.log_event(
            run_id=run_id,
            tenant_id=tenant_id,
            event_type="task_submitted",
            details={
                "task": submission.task,
                "workflow_id": submission.workflow_id
            }
        )
        
        # Queue async execution via background task (P1 integration)
        if background_tasks:
            background_tasks.add_task(
                execute_task_async,
                run_id=run_id,
                initial_state=initial_state
            )
        
        logger.info(f"Task {run_id} submitted by tenant {tenant_id}")
        
        return TaskStatusResponse(
            run_id=run_id,
            status="submitted",
            progress="Queued for processing",
            current_node="orchestrator",
            requires_approval=False,
            created_at=initial_state["created_at"],
            updated_at=initial_state["updated_at"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Task submission error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Submission failed: {str(e)}")


# ============================================================================
# ENDPOINT 3: GET TASK STATUS
# ============================================================================

@app.get("/status/{run_id}", response_model=TaskStatusResponse)
async def get_task_status(
    run_id: str,
    tenant_id: str = Depends(get_tenant_id_from_token)
):
    """
    Poll task status by run_id.
    
    Returns:
    - Current status (submitted, processing, awaiting_approval, completed, failed)
    - Progress indicator
    - Approval URL if HITL is triggered
    - Final result when complete
    """
    try:
        # Retrieve task from store
        task = tasks_store.get(run_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {run_id} not found")
        
        # Verify tenant ownership
        if task["tenant_id"] != tenant_id:
            raise HTTPException(status_code=403, detail="Unauthorized")
        
        # Build response
        approval_url = None
        if task.get("requires_human_approval"):
            approval_url = f"/approve/{run_id}"
        
        return TaskStatusResponse(
            run_id=run_id,
            status=task.get("status", "processing"),
            progress=task.get("progress", None),
            current_node=task.get("current_node", None),
            requires_approval=task.get("requires_human_approval", False),
            approval_url=approval_url,
            result=task.get("final_output", None),
            error=task.get("error", None),
            created_at=task.get("created_at"),
            updated_at=task.get("updated_at")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINT 4: APPROVE TASK (HITL)
# ============================================================================

@app.post("/approve/{run_id}", response_model=ApprovalResponse)
async def approve_task(
    run_id: str,
    approval: ApprovalRequest,
    tenant_id: str = Depends(get_tenant_id_from_token),
    background_tasks: BackgroundTasks = None
):
    """
    Approve or reject a task waiting for human approval (HITL).
    
    This endpoint is called by the Admin Dashboard when a high-risk action
    (e.g., "Refund Customer", "Update Database") requires approval.
    
    Flow:
    1. Verify task exists and is in "awaiting_approval" status
    2. Verify tenant ownership
    3. Update approval status
    4. Resume LangGraph execution via state_manager.resume_workflow()
    """
    try:
        # Retrieve task
        task = tasks_store.get(run_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {run_id} not found")
        
        # Verify tenant ownership
        if task["tenant_id"] != tenant_id:
            raise HTTPException(status_code=403, detail="Unauthorized")
        
        # Verify task is awaiting approval
        if task.get("status") != "awaiting_approval":
            raise HTTPException(
                status_code=400,
                detail=f"Task is in '{task.get('status')}' status, not awaiting approval"
            )
        
        # Update approval status
        approval_timestamp = datetime.now()
        task["approval_status"] = "approved" if approval.approved else "rejected"
        task["approval_reason"] = approval.reason
        task["approval_notes"] = approval.notes
        task["approved_at"] = approval_timestamp.isoformat()
        task["updated_at"] = approval_timestamp.isoformat()
        
        # Log approval event
        observability.log_event(
            run_id=run_id,
            tenant_id=tenant_id,
            event_type="approval_decision",
            details={
                "approved": approval.approved,
                "reason": approval.reason,
                "notes": approval.notes
            }
        )
        
        if approval.approved:
            # Resume workflow execution via state_manager
            # This will be integrated with P3 (state_manager.resume_workflow())
            task["status"] = "processing"
            task["progress"] = "Resumed after approval"
            
            # Queue resumption in background
            if background_tasks:
                background_tasks.add_task(
                    resume_workflow_after_approval,
                    run_id=run_id,
                    task_state=task
                )
            
            message = "Task approved and resuming execution"
        else:
            task["status"] = "rejected"
            task["progress"] = f"Rejected: {approval.reason}"
            message = "Task rejected"
        
        logger.info(f"Task {run_id} {task['approval_status']} by tenant {tenant_id}")
        
        return ApprovalResponse(
            run_id=run_id,
            status=task["status"],
            message=message,
            approved_at=approval_timestamp
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Approval error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# BACKGROUND TASK EXECUTION FUNCTIONS
# ============================================================================

async def execute_task_async(run_id: str, initial_state: Dict[str, Any]):
    """
    Execute task asynchronously in the background.
    This will call P1's orchestrator to run the LangGraph DAG.
    
    Placeholder for P1 integration:
    from src.orchestrator import OrchestrationEngine
    orchestrator = OrchestrationEngine()
    result = await orchestrator.execute_dag(initial_state)
    """
    try:
        logger.info(f"Starting async execution for task {run_id}")
        
        # TODO: Import from P1
        # from src.orchestrator import execute_dag
        # await execute_dag(initial_state)
        
        # DEMO PLACEHOLDER: Simulate processing
        tasks_store[run_id]["status"] = "processing"
        tasks_store[run_id]["progress"] = "Analyzing request..."
        
    except Exception as e:
        logger.error(f"Async execution error for {run_id}: {str(e)}")
        tasks_store[run_id]["status"] = "failed"
        tasks_store[run_id]["error"] = str(e)


async def resume_workflow_after_approval(run_id: str, task_state: Dict[str, Any]):
    """
    Resume LangGraph execution after approval.
    
    Placeholder for P3 integration:
    from src.memory.state import StateManager
    state_manager = StateManager()
    await state_manager.resume_workflow(run_id, task_state)
    """
    try:
        logger.info(f"Resuming workflow for task {run_id} after approval")
        
        # TODO: Import from P3
        # from src.memory.state import StateManager
        # state_manager = StateManager()
        # await state_manager.resume_workflow(run_id, task_state)
        
        # DEMO PLACEHOLDER
        tasks_store[run_id]["progress"] = "Executing action..."
        
    except Exception as e:
        logger.error(f"Resumption error for {run_id}: {str(e)}")
        tasks_store[run_id]["status"] = "failed"
        tasks_store[run_id]["error"] = str(e)


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Standard HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "timestamp": datetime.now().isoformat()
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Catch-all exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "timestamp": datetime.now().isoformat()
        },
    )


# ============================================================================
# STARTUP/SHUTDOWN HOOKS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize services on app startup"""
    logger.info("Agentic OS Gateway starting...")
    
    # Load tenant configurations
    config_loader.load_all_configs()
    logger.info("Tenant configurations loaded")
    
    # Initialize observability
    observability.initialize()
    logger.info("Observability tracker initialized")
    
    # Initialize state manager
    state_manager.initialize()
    logger.info("State manager initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on app shutdown"""
    logger.info("Agentic OS Gateway shutting down...")
    
    # Graceful shutdown
    await state_manager.cleanup()
    logger.info("State manager cleaned up")


# ============================================================================
# ROOT ENDPOINT FOR TESTING
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint for basic connectivity check"""
    return {
        "message": "Agentic OS Gateway is running",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "submit_task": "POST /submit",
            "get_status": "GET /status/{run_id}",
            "approve_task": "POST /approve/{run_id}",
            "docs": "/docs",
            "openapi": "/openapi.json"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
# src/agents/schemas.py
from pydantic import BaseModel
from typing import Optional, List, Literal, Dict, Any

class TaskSubmission(BaseModel):
    tenant_id: str
    task: str
    workflow_id: str = "default"

class AgentIO(BaseModel):
    input: Dict[str, Any]
    output: Dict[str, Any]
    status: Literal["success", "failed", "pending"]
    tool_signatures: List[str]

class MemoryCard(BaseModel):
    input_hash: str
    intent_embedding: Optional[List[float]]
    cached_output: Dict[str, Any]
    hit_type: Literal["exact", "semantic", "none"]

class Checkpoint(BaseModel):
    run_id: str
    node_id: str
    status: Literal["running", "paused", "approved", "failed"]
    payload: Dict[str, Any]

class ToolMeta(BaseModel):
    name: str
    description: str
    allowed_tenants: List[str]
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    embedding: Optional[List[float]] = None

class AgentResult(BaseModel):
    agent_name: str
    status: Literal["success", "failed"]
    output: Dict[str, Any]
    tools_used: List[str]
    error: Optional[str] = None
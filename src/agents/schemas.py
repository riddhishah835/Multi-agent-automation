class TaskSubmission(BaseModel):
	tenant_id: str
	task: str
	workflow_id: str = "default"

class AgentIO(BaseModel):
	input: dict
	output: dict
	status: Literal["success", "failed", "pending"]
	tool_signatures: List[str]

class MemoryCard(BaseModel):
	input_hash: str
	intent_embedding: Optional[List[float]]
	cached_output: dict
	hit_type: Literal["exact", "semantic", "none"]

class Checkpoint(BaseModel):
	run_id: str
	node_id: str
	status: Literal["running", "paused", "approved", "failed"]
	payload: dict

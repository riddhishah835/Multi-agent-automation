"""
State Manager
Handles: State checkpointing, workflow resumption, HITL coordination

Note: This is a placeholder for Person 3's implementation.
Person 3 will implement the full memory layer with Redis/FAISS integration.
"""

import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class StateManager:
    """
    Manages workflow state, checkpointing, and resumption.
    
    Responsibilities:
    1. Save checkpoints of workflow execution state
    2. Resume interrupted workflows from checkpoints
    3. Coordinate with HITL approval system
    4. Integrate with P1's LangGraph for state persistence
    
    Implementation by Person 3:
    - Use LangGraph's PostgreSQL or SQLite checkpointer
    - Implement semantic caching with Redis
    - Manage HITL state transitions
    """
    
    def __init__(self, checkpoint_dir: str = "checkpoints"):
        """
        Initialize state manager.
        
        Args:
            checkpoint_dir: Directory to store state checkpoints
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.state_cache: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"StateManager initialized with checkpoint directory: {self.checkpoint_dir}")
    
    def initialize(self):
        """Initialize the state manager at application startup"""
        logger.info("StateManager initialization complete")
    
    def save_checkpoint(
        self,
        run_id: str,
        node_id: str,
        state: Dict[str, Any],
        status: str = "paused"
    ) -> str:
        """
        Save a checkpoint of the current workflow state.
        Called by LangGraph after each node execution.
        
        Args:
            run_id: Unique task run ID
            node_id: Current graph node ID
            state: Complete workflow state dictionary
            status: Current status (running, paused, awaiting_approval, completed, failed)
        
        Returns:
            Checkpoint ID (same as run_id)
        """
        try:
            checkpoint = {
                "run_id": run_id,
                "node_id": node_id,
                "status": status,
                "timestamp": datetime.now().isoformat(),
                "state": state
            }
            
            # Save to file (will be replaced with database in production)
            checkpoint_file = self.checkpoint_dir / f"{run_id}_{node_id}.json"
            with open(checkpoint_file, 'w') as f:
                json.dump(checkpoint, f, indent=2, default=str)
            
            # Also cache in memory for fast access
            cache_key = f"{run_id}:{node_id}"
            self.state_cache[cache_key] = checkpoint
            
            logger.info(f"Checkpoint saved: {run_id} at node {node_id}")
            return run_id
        
        except Exception as e:
            logger.error(f"Failed to save checkpoint for {run_id}: {str(e)}")
            raise
    
    def load_checkpoint(self, run_id: str, node_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Load a checkpoint from disk or cache.
        Called when resuming a workflow.
        
        Args:
            run_id: Unique task run ID
            node_id: Optional specific node to load. If None, loads latest.
        
        Returns:
            Checkpoint dictionary, or None if not found
        """
        try:
            # Try cache first
            cache_key = f"{run_id}:{node_id}" if node_id else run_id
            if cache_key in self.state_cache:
                logger.debug(f"Checkpoint loaded from cache: {run_id}")
                return self.state_cache[cache_key]
            
            # Load from file
            if node_id:
                checkpoint_file = self.checkpoint_dir / f"{run_id}_{node_id}.json"
            else:
                # Find latest checkpoint for this run
                checkpoints = list(self.checkpoint_dir.glob(f"{run_id}_*.json"))
                if not checkpoints:
                    logger.warning(f"No checkpoints found for run {run_id}")
                    return None
                checkpoint_file = sorted(checkpoints)[-1]  # Latest by modification time
            
            if checkpoint_file.exists():
                with open(checkpoint_file, 'r') as f:
                    checkpoint = json.load(f)
                
                # Cache it
                self.state_cache[cache_key] = checkpoint
                logger.info(f"Checkpoint loaded: {checkpoint_file}")
                return checkpoint
            
            logger.warning(f"Checkpoint file not found: {checkpoint_file}")
            return None
        
        except Exception as e:
            logger.error(f"Failed to load checkpoint for {run_id}: {str(e)}")
            return None
    
    async def resume_workflow(
        self,
        run_id: str,
        state: Dict[str, Any],
        node_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Resume a paused workflow from a checkpoint.
        Called by the HITL approval endpoint when an approval is granted.
        
        Args:
            run_id: Unique task run ID
            state: Updated state (with approval status)
            node_id: Optional specific node to resume from
        
        Returns:
            Updated state after resumption
        """
        try:
            logger.info(f"Resuming workflow: {run_id}")
            
            # Load latest checkpoint
            checkpoint = self.load_checkpoint(run_id, node_id)
            if not checkpoint:
                raise Exception(f"No checkpoint found for {run_id}")
            
            # Merge approval state into checkpoint state
            merged_state = {
                **checkpoint["state"],
                **state,
                "status": "processing",
                "approval_status": "approved",
                "resumed_at": datetime.now().isoformat()
            }
            
            # TODO: Resume LangGraph execution
            # This will call P1's orchestrator.execute_dag_from_node()
            # with the merged state
            
            logger.info(f"Workflow {run_id} resumed successfully")
            return merged_state
        
        except Exception as e:
            logger.error(f"Failed to resume workflow {run_id}: {str(e)}")
            raise
    
    def mark_for_approval(
        self,
        run_id: str,
        node_id: str,
        state: Dict[str, Any],
        approval_reason: str
    ) -> str:
        """
        Mark a workflow as awaiting human approval.
        Called by the Compliance Agent when a high-risk action is detected.
        
        Args:
            run_id: Unique task run ID
            node_id: Current node ID
            state: Current workflow state
            approval_reason: Why approval is needed
        
        Returns:
            Checkpoint ID
        """
        try:
            # Save checkpoint with approval status
            state_with_approval = {
                **state,
                "requires_human_approval": True,
                "approval_reason": approval_reason,
                "approval_requested_at": datetime.now().isoformat()
            }
            
            checkpoint_id = self.save_checkpoint(
                run_id=run_id,
                node_id=node_id,
                state=state_with_approval,
                status="awaiting_approval"
            )
            
            logger.info(f"Workflow {run_id} marked for approval: {approval_reason}")
            return checkpoint_id
        
        except Exception as e:
            logger.error(f"Failed to mark workflow for approval: {str(e)}")
            raise
    
    def get_workflow_status(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current status of a workflow.
        
        Args:
            run_id: Unique task run ID
        
        Returns:
            Status dictionary with current state and node info
        """
        try:
            checkpoint = self.load_checkpoint(run_id)
            if not checkpoint:
                return None
            
            return {
                "run_id": run_id,
                "current_node": checkpoint.get("node_id"),
                "status": checkpoint.get("status"),
                "last_updated": checkpoint.get("timestamp"),
                "requires_approval": checkpoint.get("state", {}).get("requires_human_approval", False),
                "approval_reason": checkpoint.get("state", {}).get("approval_reason")
            }
        
        except Exception as e:
            logger.error(f"Failed to get workflow status: {str(e)}")
            return None
    
    def list_waiting_approvals(self) -> list:
        """
        List all workflows currently awaiting human approval.
        Useful for admin dashboards.
        
        Returns:
            List of (run_id, approval_reason) tuples
        """
        try:
            waiting = []
            
            # Scan all checkpoint files
            for checkpoint_file in self.checkpoint_dir.glob("*.json"):
                try:
                    with open(checkpoint_file, 'r') as f:
                        checkpoint = json.load(f)
                    
                    if checkpoint.get("status") == "awaiting_approval":
                        waiting.append({
                            "run_id": checkpoint["run_id"],
                            "node_id": checkpoint["node_id"],
                            "approval_reason": checkpoint.get("state", {}).get("approval_reason"),
                            "timestamp": checkpoint.get("timestamp")
                        })
                
                except Exception as e:
                    logger.warning(f"Failed to read checkpoint {checkpoint_file}: {str(e)}")
            
            logger.info(f"Found {len(waiting)} workflows awaiting approval")
            return waiting
        
        except Exception as e:
            logger.error(f"Failed to list waiting approvals: {str(e)}")
            return []
    
    def cleanup(self):
        """Clean up resources (called on shutdown)"""
        logger.info("StateManager cleaned up")
    
    # ========================================================================
    # SEMANTIC CACHING METHODS (P3 to implement with Redis/FAISS)
    # ========================================================================
    
    def cache_task_result(
        self,
        run_id: str,
        request_hash: str,
        intent_embedding: Optional[list],
        result: Dict[str, Any],
        ttl_seconds: int = 604800  # 7 days
    ):
        """
        Cache a task result for semantic matching.
        Called after task completion.
        
        Implementation by P3:
        - Store in Redis with TTL
        - Generate vector embedding of request
        - Index in FAISS for semantic search
        
        Args:
            run_id: Task run ID
            request_hash: Hash of original request
            intent_embedding: Vector embedding of request intent
            result: Final task output
            ttl_seconds: Time to live for cache entry
        """
        logger.debug(f"Caching result for run {run_id}")
        # TODO: P3 Implementation
    
    def find_cached_result(
        self,
        request_hash: str,
        intent_embedding: Optional[list],
        similarity_threshold: float = 0.90
    ) -> Optional[Dict[str, Any]]:
        """
        Find a cached result by semantic similarity.
        Called before running orchestrator.
        
        Implementation by P3:
        - Check exact hash match first (L1 cache)
        - Perform cosine similarity search in FAISS (L2 cache)
        - Return result if similarity > threshold
        
        Args:
            request_hash: Hash of request
            intent_embedding: Vector embedding of request
            similarity_threshold: Minimum similarity to consider a match
        
        Returns:
            Cached result, or None if not found or below threshold
        """
        logger.debug(f"Searching for cached result similar to {request_hash}")
        # TODO: P3 Implementation
        return None


# ============================================================================
# PLACEHOLDER FOR P3 INTEGRATION
# ============================================================================

class P3_IntegrationPlaceholder:
    """
    Placeholder showing where P3 (Memory Layer & HITL) will integrate.
    
    P3 Deliverables:
    - memory_layer.py: L1 hash cache + L2 FAISS semantic cache
    - trace_emitter.py: Structured logging of execution traces
    - state_manager.py: Enhanced with Redis/FAISS integration
    - hitl_handler.py: HITL approval flow coordination
    
    Integration points:
    1. StateManager.cache_task_result() - Write to Redis + FAISS
    2. StateManager.find_cached_result() - Query Redis/FAISS
    3. StateManager.save_checkpoint() - Use LangGraph checkpointer
    4. StateManager.resume_workflow() - Resume from LangGraph state
    """
    pass


if __name__ == "__main__":
    # Example usage
    state_manager = StateManager()
    
    # Simulate a workflow
    run_id = "test-run-001"
    state = {
        "tenant_id": "acme",
        "original_request": "Create a customer refund",
        "current_plan": ["validate_refund", "process_payment", "send_confirmation"],
        "gathered_context": "Customer order found, valid refund reason"
    }
    
    # Save checkpoint
    checkpoint_id = state_manager.save_checkpoint(
        run_id=run_id,
        node_id="execution_agent",
        state=state,
        status="paused"
    )
    print(f"Checkpoint saved: {checkpoint_id}")
    
    # Load checkpoint
    loaded = state_manager.load_checkpoint(run_id)
    print(f"Loaded checkpoint: {json.dumps(loaded, indent=2, default=str)}")
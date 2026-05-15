"""
State Manager — Checkpoint store, HITL flagging, and resume logic.
Part of Phase 3: Memory, State & Governance.

Task lifecycle states:
  pending → running → hitl_paused → approved | rejected → completed | failed
"""

import json
import logging
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List

# Setup Logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class TaskStatus(str, Enum):
    """Deterministic states for the Agentic OS lifecycle."""
    PENDING = "pending"
    RUNNING = "running"
    HITL_PAUSED = "hitl_paused"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"

class StateManager:
    """
    Manages workflow state, checkpointing, and resumption for the Compliance Service.
    
    Responsibilities:
    1. Save millisecond-precision checkpoints of workflow execution.
    2. Resume interrupted workflows from the absolute latest state.
    3. Coordinate Human-in-the-Loop (HITL) transitions.
    4. Provide audit-ready state snapshots.
    """

    def __init__(self, checkpoint_dir: str = "checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        # In-memory cache for fast hot-access
        self.state_cache: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"🚀 StateManager initialized. Path: {self.checkpoint_dir}")

    def save_checkpoint(
        self,
        run_id: str,
        node_id: str,
        state: Dict[str, Any],
        status: TaskStatus = TaskStatus.RUNNING
    ) -> str:
        """
        Saves a serialized snapshot of the current workflow.
        Uses a timestamp-prefixed filename to ensure perfect chronological sorting.
        """
        try:
            timestamp_ms = int(time.time() * 1000)
            checkpoint = {
                "run_id": run_id,
                "node_id": node_id,
                "status": status.value,
                "timestamp": datetime.now().isoformat(),
                "unix_ts": timestamp_ms,
                "state": state
            }
            
            # Pattern: runid_timestamp_nodeid.json (ensures latest is always sorted last)
            filename = f"{run_id}_{timestamp_ms}_{node_id}.json"
            checkpoint_file = self.checkpoint_dir / filename
            
            with open(checkpoint_file, 'w') as f:
                json.dump(checkpoint, f, indent=2, default=str)
            
            # Hot-cache the latest state
            self.state_cache[run_id] = checkpoint
            
            logger.info(f"💾 Checkpoint saved | Run: {run_id} | Node: {node_id} | Status: {status.value}")
            return run_id
        
        except Exception as e:
            logger.error(f"❌ Failed to save checkpoint for {run_id}: {str(e)}")
            raise

    def load_checkpoint(self, run_id: str, node_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Loads the latest checkpoint for a run, or a specific node if requested.
        """
        try:
            # Pattern match files for this specific run_id
            checkpoints = list(self.checkpoint_dir.glob(f"{run_id}_*.json"))
            if not checkpoints:
                logger.warning(f"⚠️ No checkpoints found for run: {run_id}")
                return None
            
            if node_id:
                # Filter for a specific node if requested
                matches = [c for c in checkpoints if node_id in c.name]
                if not matches: return None
                checkpoint_file = sorted(matches)[-1]
            else:
                # Chronological sort based on the timestamp in filename
                checkpoint_file = sorted(checkpoints)[-1]
            
            with open(checkpoint_file, 'r') as f:
                data = json.load(f)
                return data

        except Exception as e:
            logger.error(f"❌ Failed to load checkpoint: {str(e)}")
            return None

    def mark_for_approval(
        self,
        run_id: str,
        node_id: str,
        state: Dict[str, Any],
        reason: str
    ) -> str:
        """
        Transitions the workflow to HITL_PAUSED.
        Called when a 'Judge Agent' flags a compliance risk.
        """
        updated_state = {
            **state,
            "hitl_metadata": {
                "flagged_at": datetime.now().isoformat(),
                "reason": reason,
                "requires_action": True
            }
        }
        return self.save_checkpoint(run_id, node_id, updated_state, status=TaskStatus.HITL_PAUSED)

    async def resume_workflow(
        self,
        run_id: str,
        decision: TaskStatus,  # APPROVED or REJECTED
        feedback: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Resumes a paused workflow based on human input.
        """
        checkpoint = self.load_checkpoint(run_id)
        if not checkpoint:
            raise ValueError(f"Cannot resume. No state found for {run_id}")

        current_state = checkpoint["state"]
        
        # Inject human decision into state
        current_state["hitl_metadata"].update({
            "decision": decision.value,
            "feedback": feedback,
            "resolved_at": datetime.now().isoformat(),
            "requires_action": False
        })

        logger.info(f"🔄 Resuming workflow {run_id} with decision: {decision.value}")
        
        # Save new state as 'RUNNING' to trigger next node in Orchestrator
        self.save_checkpoint(run_id, checkpoint["node_id"], current_state, status=TaskStatus.RUNNING)
        return current_state

    def get_full_state_summary(self, run_id: str) -> Dict[str, Any]:
        """
        Returns the specific state object needed for API responses.
        As requested: includes task info, latest checkpoint, and HITL records.
        """
        checkpoint = self.load_checkpoint(run_id)
        if not checkpoint:
            return {"error": "Run not found"}

        return {
            "run_id": run_id,
            "status": checkpoint.get("status"),
            "current_node": checkpoint.get("node_id"),
            "last_updated": checkpoint.get("timestamp"),
            "checkpoint": checkpoint.get("state"),
            "hitl": checkpoint.get("state", {}).get("hitl_metadata", {}),
            "is_blocked": checkpoint.get("status") == TaskStatus.HITL_PAUSED
        }

    def list_active_hitl(self) -> List[Dict[str, Any]]:
        """Scans for all workflows currently awaiting human approval."""
        active_requests = []
        # Find all current checkpoints
        for file in self.checkpoint_dir.glob("*.json"):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    if data.get("status") == TaskStatus.HITL_PAUSED:
                        active_requests.append({
                            "run_id": data["run_id"],
                            "reason": data["state"]["hitl_metadata"]["reason"],
                            "timestamp": data["timestamp"]
                        })
            except: continue
        return active_requests

# ========================================================================
# SEMANTIC CACHING STUBS (For P3 integration with Redis/Qdrant)
# ========================================================================

    def cache_final_result(self, request_hash: str, result: Dict[str, Any]):
        """Future: Store successful audits in Qdrant for semantic reuse."""
        pass

    def find_cached_audit(self, request_hash: str) -> Optional[Dict[str, Any]]:
        """Future: Look up if this vendor/policy combo has been audited before."""
        return None

# ========================================================================
# TEST EXECUTION
# ========================================================================
if __name__ == "__main__":
    sm = StateManager()
    
    # 1. Simulate Start
    test_id = "audit_volvo_001"
    initial_state = {"vendor": "Volvo", "policy": "SOC2_v3"}
    sm.save_checkpoint(test_id, "ingestion_node", initial_state, status=TaskStatus.RUNNING)
    
    # 2. Simulate HITL Trigger
    sm.mark_for_approval(test_id, "judge_node", initial_state, "Encryption key length not specified in SOC2")
    
    # 3. Check Status
    print(json.dumps(sm.get_full_state_summary(test_id), indent=2))
"""
Trace Logger — emits structured JSON to stdout + rotating log file.

Each log line is a single JSON object with at minimum:
  ts          ISO-8601 timestamp (UTC)
  component   caller module (e.g. "orchestrator")
  event       event name
  run_id      correlation ID for the specific audit workflow
  tenant_id   the client the audit belongs to
  …kwargs     caller-supplied fields
"""

from __future__ import annotations

import json
import logging
import os
import sys
import traceback
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Any, Optional

LOG_DIR  = os.getenv("LOG_DIR", "logs")
LOG_FILE = os.path.join(LOG_DIR, "traces.jsonl")
MAX_BYTES   = 10 * 1024 * 1024   # 10 MB per file
BACKUP_COUNT = 5

os.makedirs(LOG_DIR, exist_ok=True)

# ── raw Python logger (no formatter — we emit pre-serialised JSON) ────────────
# Use a specific namespace to avoid collisions with external libraries
_root = logging.getLogger("agentic_os.trace")
_root.setLevel(logging.DEBUG)

if not _root.handlers:
    _fh = RotatingFileHandler(LOG_FILE, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT)
    _fh.setLevel(logging.DEBUG)
    _root.addHandler(_fh)

    _sh = logging.StreamHandler(sys.stdout)
    _sh.setLevel(logging.INFO)
    _root.addHandler(_sh)


class TraceLogger:
    """
    Thin wrapper that injects *component*, *tenant_id*, and *run_id* into every log call.

    Usage
    -----
    logger = TraceLogger(component="memory.layer", tenant_id="acme", run_id="audit_123")
    logger.log_event(event="l1_get", cache_key="abc", hit=True, latency_ms=0.4)
    """

    def __init__(self, component: str, tenant_id: Optional[str] = None, run_id: Optional[str] = None) -> None:
        self._component = component
        self._tenant_id = tenant_id or "system"
        self._run_id = run_id or "global"

    def log_event(self, event: str, **kwargs: Any) -> None:
        record = {
            "ts":        datetime.now(timezone.utc).isoformat(),
            "component": self._component,
            "tenant_id": self._tenant_id,
            "run_id":    self._run_id,
            "event":     event,
            **kwargs,
        }
        line = json.dumps(record, default=str)
        _root.info(line)

    # ── convenience aliases ───────────────────────────────────────────────────

    def log_tool_call(
        self,
        *,
        tool_name: str,
        input_args: Dict[str, Any],
        output: Any,
        latency_ms: float,
        cache_source: str = "miss",
    ) -> None:
        self.log_event(
            event="tool_call",
            tool_name=tool_name,
            input_preview=str(input_args)[:200],
            output_preview=str(output)[:200],
            latency_ms=latency_ms,
            cache_source=cache_source,
        )

    def log_llm_call(
        self,
        *,
        agent_name: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
    ) -> None:
        """Tracks cost and performance of the core Judge/Context agents."""
        self.log_event(
            event="llm_execution",
            agent_name=agent_name,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            latency_ms=latency_ms,
        )

    def log_hitl(self, *, reason: str, node_id: str) -> None:
        self.log_event(
            event="hitl_flagged",
            node_id=node_id,
            reason=reason,
        )

    def log_approval(self, *, approved_by: str, action: str, feedback: Optional[str] = None) -> None:
        self.log_event(
            event="hitl_resolved",
            approved_by=approved_by,
            action=action,
            feedback=feedback,
        )

    def log_state_transition(
        self, *, from_state: str, to_state: str, node_id: str
    ) -> None:
        self.log_event(
            event="state_transition",
            node_id=node_id,
            from_state=from_state,
            to_state=to_state,
        )
        
    def log_error(self, *, message: str, error: Exception) -> None:
        """Ensures exceptions are captured cleanly in the JSON trace."""
        self.log_event(
            event="error",
            message=message,
            error_type=type(error).__name__,
            error_msg=str(error),
            traceback="".join(traceback.format_exception(type(error), error, error.__traceback__))
        )
"""
Trace Logger — emits structured JSON to stdout + rotating log file.

Each log line is a single JSON object with at minimum:
  ts          ISO-8601 timestamp (UTC)
  component   caller module (e.g. "memory.layer")
  event       event name
  …kwargs     caller-supplied fields (input_hash, tool_signature, latency_ms, …)
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Any

LOG_DIR  = os.getenv("LOG_DIR", "logs")
LOG_FILE = os.path.join(LOG_DIR, "trace.jsonl")
MAX_BYTES   = 10 * 1024 * 1024   # 10 MB per file
BACKUP_COUNT = 5

os.makedirs(LOG_DIR, exist_ok=True)

# ── raw Python logger (no formatter — we emit pre-serialised JSON) ────────────
_root = logging.getLogger("trace")
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
    Thin wrapper that injects *component* into every log call.

    Usage
    -----
    logger = TraceLogger(component="memory.layer")
    logger.log_event(event="l1_get", cache_key="abc123", hit=True, latency_ms=0.4)
    """

    def __init__(self, component: str) -> None:
        self._component = component

    def log_event(self, event: str, **kwargs: Any) -> None:
        record = {
            "ts":        datetime.now(timezone.utc).isoformat(),
            "component": self._component,
            "event":     event,
            **kwargs,
        }
        line = json.dumps(record, default=str)
        _root.info(line)

    # ── convenience aliases ───────────────────────────────────────────────────

    def log_tool_call(
        self,
        *,
        input_hash: str,
        tool_signature: str,
        output: Any,
        latency_ms: float,
        cache_source: str = "miss",
    ) -> None:
        self.log_event(
            event="tool_call",
            input_hash=input_hash,
            tool_signature=tool_signature,
            output_preview=str(output)[:200],
            latency_ms=latency_ms,
            cache_source=cache_source,
        )

    def log_hitl(self, *, task_id: str, reason: str, flagged_by: str) -> None:
        self.log_event(
            event="hitl_flagged",
            task_id=task_id,
            reason=reason,
            flagged_by=flagged_by,
        )

    def log_approval(self, *, task_id: str, approved_by: str, action: str) -> None:
        self.log_event(
            event="hitl_approved",
            task_id=task_id,
            approved_by=approved_by,
            action=action,
        )

    def log_state_transition(
        self, *, task_id: str, from_state: str, to_state: str
    ) -> None:
        self.log_event(
            event="state_transition",
            task_id=task_id,
            from_state=from_state,
            to_state=to_state,
        )
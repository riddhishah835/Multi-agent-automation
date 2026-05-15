"""
Observability Module
Handles: Structured logging, request tracing, token counting, cost tracking
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
import time
from enum import Enum
import hashlib

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

class EventType(str, Enum):
    """Types of observable events"""
    TASK_SUBMITTED = "task_submitted"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    AGENT_CALLED = "agent_called"
    TOOL_CALLED = "tool_called"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_DECISION = "approval_decision"
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    STATE_CHECKPOINT = "state_checkpoint"
    ERROR = "error"
    WARNING = "warning"


class LogLevel(str, Enum):
    """Log levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# Token costs (as of latest GPT pricing)
TOKEN_COSTS = {
    "gpt-4": {"input": 0.00003, "output": 0.00006},
    "gpt-4-turbo": {"input": 0.00001, "output": 0.00003},
    "gpt-3.5-turbo": {"input": 0.0000005, "output": 0.0000015},
    "claude-3-opus": {"input": 0.000015, "output": 0.000075},
    "claude-3-sonnet": {"input": 0.000003, "output": 0.000015},
    "claude-3-haiku": {"input": 0.00000025, "output": 0.00000125},
}


# ============================================================================
# TRACE & EVENT SCHEMAS
# ============================================================================

class Trace:
    """Represents a single execution trace"""
    
    def __init__(
        self,
        run_id: str,
        tenant_id: str,
        event_type: str,
        node_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        tool_name: Optional[str] = None
    ):
        self.run_id = run_id
        self.tenant_id = tenant_id
        self.event_type = event_type
        self.node_id = node_id
        self.agent_name = agent_name
        self.tool_name = tool_name
        self.timestamp = datetime.now()
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.duration_ms: Optional[float] = None
        
        # Input/Output
        self.input_data: Optional[Dict[str, Any]] = None
        self.output_data: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        
        # Tokens & Cost
        self.input_tokens: int = 0
        self.output_tokens: int = 0
        self.model: str = "unknown"
        self.cost: float = 0.0
        
        # Metadata
        self.metadata: Dict[str, Any] = {}
    
    def finish(self):
        """Mark trace as finished and calculate duration"""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert trace to dictionary"""
        return {
            "run_id": self.run_id,
            "tenant_id": self.tenant_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "node_id": self.node_id,
            "agent_name": self.agent_name,
            "tool_name": self.tool_name,
            "duration_ms": self.duration_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.input_tokens + self.output_tokens,
            "model": self.model,
            "cost": f"${self.cost:.6f}",
            "error": self.error,
            "metadata": self.metadata
        }


class ObservabilityTracker:
    """
    Central observability system for tracking execution traces,
    token usage, costs, and system metrics.
    """
    
    def __init__(
        self,
        log_file: str = "logs/traces.jsonl",
        metrics_file: str = "logs/metrics.json"
    ):
        """
        Initialize observability tracker.
        
        Args:
            log_file: Path to JSONL trace log file
            metrics_file: Path to metrics summary file
        """
        self.log_file = Path(log_file)
        self.metrics_file = Path(metrics_file)
        self.traces: Dict[str, List[Trace]] = {}  # run_id -> list of traces
        self.metrics: Dict[str, Any] = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_latency_ms": 0.0
        }
        
        # Ensure log directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize structured logger
        self._setup_logger()
        
        logger.info(f"ObservabilityTracker initialized with log file: {self.log_file}")
    
    def _setup_logger(self):
        """Configure structured JSON logger"""
        # Remove existing handlers
        logger.handlers.clear()
        
        # Add file handler with JSON formatting
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.INFO)
        
        # JSON formatter
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_data = {
                    "timestamp": datetime.now().isoformat(),
                    "level": record.levelname,
                    "message": record.getMessage()
                }
                return json.dumps(log_data)
        
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)
        
        # Also add console handler for debugging
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        logger.addHandler(console_handler)
    
    def initialize(self):
        """Initialize observability system at startup"""
        logger.info("Observability system initialized")
    
    def start_trace(
        self,
        run_id: str,
        tenant_id: str,
        event_type: str,
        node_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        tool_name: Optional[str] = None
    ) -> Trace:
        """
        Start a new trace for an operation.
        
        Args:
            run_id: Unique task run ID
            tenant_id: Tenant identifier
            event_type: Type of event
            node_id: Optional graph node identifier
            agent_name: Optional agent name
            tool_name: Optional tool name
        
        Returns:
            Trace object for tracking
        """
        trace = Trace(
            run_id=run_id,
            tenant_id=tenant_id,
            event_type=event_type,
            node_id=node_id,
            agent_name=agent_name,
            tool_name=tool_name
        )
        
        # Store trace
        if run_id not in self.traces:
            self.traces[run_id] = []
        self.traces[run_id].append(trace)
        
        logger.debug(f"Trace started: {event_type} for run {run_id}")
        
        return trace
    
    def finish_trace(
        self,
        trace: Trace,
        output_data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        model: str = "unknown"
    ):
        """
        Finish a trace and record metrics.
        
        Args:
            trace: The Trace object to finish
            output_data: Optional output data
            error: Optional error message
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens used
            model: Model name (for cost calculation)
        """
        trace.output_data = output_data
        trace.error = error
        trace.input_tokens = input_tokens
        trace.output_tokens = output_tokens
        trace.model = model
        
        # Calculate cost
        if model in TOKEN_COSTS:
            costs = TOKEN_COSTS[model]
            trace.cost = (
                (input_tokens * costs["input"]) +
                (output_tokens * costs["output"])
            )
        
        trace.finish()
        
        # Update metrics
        self._update_metrics(trace)
        
        # Write to log
        self._write_trace_log(trace)
        
        logger.debug(f"Trace finished: {trace.event_type} for run {trace.run_id}")
    
    def _update_metrics(self, trace: Trace):
        """Update global metrics from trace"""
        total_tokens = trace.input_tokens + trace.output_tokens
        
        self.metrics["total_tokens"] += total_tokens
        self.metrics["total_cost"] += trace.cost
        
        if trace.event_type == EventType.TASK_COMPLETED:
            self.metrics["completed_tasks"] += 1
        elif trace.event_type == EventType.TASK_FAILED:
            self.metrics["failed_tasks"] += 1
        elif trace.event_type == EventType.CACHE_HIT:
            self.metrics["cache_hits"] += 1
        elif trace.event_type == EventType.CACHE_MISS:
            self.metrics["cache_misses"] += 1
    
    def _write_trace_log(self, trace: Trace):
        """Write trace to JSONL log file"""
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(trace.to_dict()) + '\n')
        except Exception as e:
            logger.error(f"Failed to write trace log: {str(e)}")
    
    def log_event(
        self,
        run_id: str,
        tenant_id: str,
        event_type: str,
        details: Optional[Dict[str, Any]] = None,
        level: str = "INFO"
    ):
        """
        Log a simple event (not a full trace).
        
        Args:
            run_id: Task run ID
            tenant_id: Tenant identifier
            event_type: Type of event
            details: Event details
            level: Log level
        """
        event = {
            "timestamp": datetime.now().isoformat(),
            "run_id": run_id,
            "tenant_id": tenant_id,
            "event_type": event_type,
            "level": level,
            "details": details or {}
        }
        
        # Write to log file
        try:
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(event) + '\n')
        except Exception as e:
            logger.error(f"Failed to log event: {str(e)}")
        
        # Also log via Python logger
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(f"Event: {event_type} - {json.dumps(details or {})}")
    
    def get_run_traces(self, run_id: str) -> List[Dict[str, Any]]:
        """
        Get all traces for a specific run.
        
        Args:
            run_id: Task run ID
        
        Returns:
            List of trace dictionaries
        """
        if run_id not in self.traces:
            return []
        
        return [trace.to_dict() for trace in self.traces[run_id]]
    
    def get_run_summary(self, run_id: str) -> Dict[str, Any]:
        """
        Get summary statistics for a run.
        
        Args:
            run_id: Task run ID
        
        Returns:
            Summary dictionary with token count, cost, duration, etc.
        """
        if run_id not in self.traces:
            return {}
        
        traces = self.traces[run_id]
        
        # Calculate totals
        total_tokens = sum(t.input_tokens + t.output_tokens for t in traces)
        total_cost = sum(t.cost for t in traces)
        total_duration = sum(t.duration_ms or 0 for t in traces)
        
        return {
            "run_id": run_id,
            "total_traces": len(traces),
            "total_tokens": total_tokens,
            "input_tokens": sum(t.input_tokens for t in traces),
            "output_tokens": sum(t.output_tokens for t in traces),
            "total_cost": f"${total_cost:.6f}",
            "total_duration_ms": total_duration,
            "avg_trace_duration_ms": total_duration / len(traces) if traces else 0,
            "events": [t.event_type for t in traces]
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get global system metrics.
        
        Returns:
            Metrics dictionary
        """
        total_tasks = self.metrics["completed_tasks"] + self.metrics["failed_tasks"]
        
        return {
            **self.metrics,
            "total_tasks": total_tasks,
            "success_rate": (
                self.metrics["completed_tasks"] / total_tasks * 100
                if total_tasks > 0 else 0
            ),
            "cache_hit_rate": (
                self.metrics["cache_hits"] / (
                    self.metrics["cache_hits"] + self.metrics["cache_misses"]
                ) * 100
                if (self.metrics["cache_hits"] + self.metrics["cache_misses"]) > 0 else 0
            ),
            "total_cost": f"${self.metrics['total_cost']:.2f}",
            "estimated_daily_cost": f"${self.metrics['total_cost'] * 100:.2f}"  # Rough estimate
        }
    
    def export_metrics(self) -> str:
        """
        Export metrics to JSON file.
        
        Returns:
            Path to metrics file
        """
        try:
            with open(self.metrics_file, 'w') as f:
                json.dump(self.get_metrics(), f, indent=2)
            logger.info(f"Metrics exported to {self.metrics_file}")
            return str(self.metrics_file)
        except Exception as e:
            logger.error(f"Failed to export metrics: {str(e)}")
            return ""
    
    def cleanup(self):
        """Clean up resources"""
        logger.info("Observability tracker cleaned up")


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def log_trace(
    run_id: str,
    tenant_id: str,
    event_type: str,
    node_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    tool_name: Optional[str] = None
) -> Trace:
    """
    Convenience function to create a trace via global tracker.
    
    Usage:
    trace = log_trace(run_id, tenant_id, "agent_called", agent_name="context")
    # ... do work ...
    finish_trace(trace, output_data=result, input_tokens=100, output_tokens=50)
    """
    # TODO: Inject global tracker instance
    pass


def finish_trace(
    trace: Trace,
    output_data: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    model: str = "unknown"
):
    """
    Convenience function to finish a trace via global tracker.
    """
    # TODO: Inject global tracker instance
    pass


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Initialize tracker
    tracker = ObservabilityTracker()
    
    # Simulate traces
    run_id = "test-run-001"
    tenant_id = "acme"
    
    # Start a trace
    trace = tracker.start_trace(
        run_id=run_id,
        tenant_id=tenant_id,
        event_type=EventType.AGENT_CALLED,
        agent_name="context"
    )
    
    # Simulate work
    time.sleep(0.1)
    
    # Finish trace
    tracker.finish_trace(
        trace=trace,
        output_data={"result": "test data"},
        input_tokens=100,
        output_tokens=50,
        model="gpt-4"
    )
    
    # Get run summary
    summary = tracker.get_run_summary(run_id)
    print(f"Run Summary: {json.dumps(summary, indent=2)}")
    
    # Get metrics
    metrics = tracker.get_metrics()
    print(f"System Metrics: {json.dumps(metrics, indent=2)}")
    
    # Export
    tracker.export_metrics()
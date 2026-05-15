# src/agents/runtime.py
from typing import Dict, Any, List
from src.agents.schemas import AgentResult, ToolMeta
from src.tools.mcp_bridge import call_tool
from src.tools.pruner import prune_tools


def _build_payload(tool_name: str, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Map a task + context dict to the right input shape for each tool."""
    mapping: Dict[str, Dict[str, Any]] = {
        "web_search":     {"query": task},
        "crm_lookup":     {"customer_id": context.get("customer_id", "C001")},
        "send_email":     {
            "to":      context.get("to", "stakeholder@company.com"),
            "subject": context.get("subject", f"Re: {task[:40]}"),
            "body":    context.get("body", "Please see the attached report."),
        },
        "pdf_reader":     {"file_path": context.get("file_path", "/tmp/doc.pdf")},
        "database_write": {
            "table":  context.get("table", "records"),
            "record": context.get("record", {"note": task}),
        },
        "slack_notify":   {
            "channel": context.get("channel", "#general"),
            "message": task,
        },
    }
    return mapping.get(tool_name, {"query": task})


def _run_agent(
    agent_name: str,
    task: str,
    tenant_id: str,
    context: Dict[str, Any] = {},
) -> AgentResult:
    """Core runner: prune tools → call each → collect results."""
    tools: List[ToolMeta] = prune_tools(task, tenant_id)
    results = {}
    errors = []

    for tool in tools:
        try:
            payload = _build_payload(tool.name, task, context)
            results[tool.name] = call_tool(tool.name, payload)
        except Exception as e:
            results[tool.name] = {"error": str(e)}
            errors.append(str(e))

    return AgentResult(
        agent_name=agent_name,
        status="failed" if errors and not results else "success",
        output={"task": task, "tool_results": results},
        tools_used=[t.name for t in tools],
        error="; ".join(errors) if errors else None,
    )


# ── The three agents P1 and P4 will call directly ────────────────────────────

def researcher_agent(task: str, tenant_id: str) -> AgentResult:
    """
    Read-only: searches web and reads documents.
    Safe — cannot mutate any external system.
    P1 calls this early in the DAG to gather context.
    """
    return _run_agent("researcher", task, tenant_id)


def data_fetcher_agent(task: str, tenant_id: str, context: Dict[str, Any] = {}) -> AgentResult:
    """
    Reads internal systems (CRM, databases).
    Medium risk — read-only but touches private data.
    P1 calls this after researcher_agent if structured data is needed.
    """
    return _run_agent("data_fetcher", task, tenant_id, context)


def content_generator_agent(task: str, tenant_id: str, context: Dict[str, Any] = {}) -> AgentResult:
    """
    Writes and dispatches content (emails, Slack, DB records).
    HIGH RISK — may call send_email or database_write.
    P1 must check HIGH_RISK_TOOLS and trigger HITL (via P3) before calling this.
    """
    return _run_agent("content_generator", task, tenant_id, context)
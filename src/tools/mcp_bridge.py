# src/tools/mcp_bridge.py
from typing import Any, Dict
from src.tools.registry import registry

# Mock API responses — replace each value with a real httpx.post() when ready
MOCK_RESPONSES: Dict[str, Any] = {
    "web_search":     {"results": ["Result A about the topic", "Result B with more detail"]},
    "crm_lookup":     {"customer": {"id": "C001", "name": "Acme Corp", "tier": "enterprise"}},
    "send_email":     {"sent": True},
    "pdf_reader":     {"text": "Extracted text from the PDF document."},
    "database_write": {"success": True},
    "slack_notify":   {"ok": True},
}


def _validate_input(tool_name: str, payload: Dict[str, Any]) -> None:
    tool = registry.get_by_name(tool_name)
    missing = [k for k in tool.input_schema if k not in payload]
    if missing:
        raise ValueError(f"Tool '{tool_name}' missing fields: {missing}")


def _validate_output(tool_name: str, result: Dict[str, Any]) -> None:
    tool = registry.get_by_name(tool_name)
    missing = [k for k in tool.output_schema if k not in result]
    if missing:
        raise ValueError(f"Tool '{tool_name}' response missing fields: {missing}")


def call_tool(tool_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute one tool call. Validates both input and output against the tool schema.

    To go live, replace the mock block with:
        import httpx
        response = httpx.post(f"http://mcp-server/{tool_name}", json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
    """
    _validate_input(tool_name, payload)

    if tool_name not in MOCK_RESPONSES:
        raise ValueError(f"No mock response for tool '{tool_name}'")
    result = MOCK_RESPONSES[tool_name]

    _validate_output(tool_name, result)
    return result
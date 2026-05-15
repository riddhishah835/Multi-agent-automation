# src/tools/registry.py
from src.agents.schemas import ToolMeta
from typing import Dict, List

RAW_TOOLS = [
    {
        "name": "web_search",
        "description": "Search the web for recent information on a topic",
        "allowed_tenants": ["*"],
        "input_schema": {"query": "string"},
        "output_schema": {"results": "list"},
    },
    {
        "name": "crm_lookup",
        "description": "Fetch customer records from CRM by customer ID or email",
        "allowed_tenants": ["tenant_demo", "tenant_acme"],
        "input_schema": {"customer_id": "string"},
        "output_schema": {"customer": "object"},
    },
    {
        "name": "send_email",
        "description": "Send an email to a recipient with subject and body",
        "allowed_tenants": ["*"],
        "input_schema": {"to": "string", "subject": "string", "body": "string"},
        "output_schema": {"sent": "bool"},
    },
    {
        "name": "pdf_reader",
        "description": "Extract text content from a PDF file",
        "allowed_tenants": ["*"],
        "input_schema": {"file_path": "string"},
        "output_schema": {"text": "string"},
    },
    {
        "name": "database_write",
        "description": "Write or update a record in the internal database",
        "allowed_tenants": ["tenant_acme"],
        "input_schema": {"table": "string", "record": "object"},
        "output_schema": {"success": "bool"},
    },
    {
        "name": "slack_notify",
        "description": "Send a Slack message to a channel",
        "allowed_tenants": ["*"],
        "input_schema": {"channel": "string", "message": "string"},
        "output_schema": {"ok": "bool"},
    },
]

# P3 imports this to know which tools require human approval before execution
HIGH_RISK_TOOLS = {"send_email", "database_write"}


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolMeta] = {}
        self._load()

    def _load(self):
        for raw in RAW_TOOLS:
            self._tools[raw["name"]] = ToolMeta(**raw)

    def get_all(self) -> List[ToolMeta]:
        return list(self._tools.values())

    def get_by_name(self, name: str) -> ToolMeta:
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not in registry")
        return self._tools[name]

    def get_for_tenant(self, tenant_id: str) -> List[ToolMeta]:
        return [
            t for t in self._tools.values()
            if "*" in t.allowed_tenants or tenant_id in t.allowed_tenants
        ]


# Single shared instance — everyone imports this object, not the class
registry = ToolRegistry()
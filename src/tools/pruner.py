"""
src/tools/pruner.py
────────────────────
Phase 2: Pruner Logic

Goal: given a task description and a tenant ID, return the MINIMAL set of
ToolMeta objects needed to complete that task.

Why this matters:
  • Keeps the agent's context window focused (lower token cost).
  • Prevents the_judge from calling a GDPR tool during a Financial-Risk audit.
  • Respects per-tenant tool access rules.

The pruner is intentionally lightweight (no LLM call). It uses keyword matching
plus the CATEGORY_TOOL_MAP in registry.py, so latency is < 1 ms.

P1 (Orchestrator) calls prune_tools() before dispatching any agent.
runtime.py calls prune_tools() inside _run_agent() for the same reason.
"""

from __future__ import annotations

import logging
from typing import List

from src.tools.registry import (
    CATEGORY_TOOL_MAP,
    ToolMeta,
    _infer_category,
    registry,
)

log = logging.getLogger(__name__)


# ── Public API ────────────────────────────────────────────────────────────────

def prune_tools(task: str, tenant_id: str) -> List[ToolMeta]:
    """
    Return the focused, tenant-filtered tool list for a given task.

    Algorithm
    ---------
    1. Infer the compliance category from `task` keywords.
    2. Resolve the canonical tool list for that category from CATEGORY_TOOL_MAP.
    3. Filter to tools the tenant is allowed to use.
    4. Sort by cost_tier (low → medium → high) so cheaper tools are preferred.

    Parameters
    ----------
    task      : Natural-language task string (e.g. "Check encryption policy in SOC2").
    tenant_id : Tenant identifier used for access-control filtering.

    Returns
    -------
    List[ToolMeta] — ordered cheapest-first, never empty (falls back to pdf_reader).
    """
    category = _infer_category(task)
    log.debug("pruner: task=%r → category=%r", task, category)

    # Tools allowed for this category
    category_tool_names: List[str] = CATEGORY_TOOL_MAP.get(category, CATEGORY_TOOL_MAP["general"])

    # Tools allowed for this tenant
    tenant_allowed: set[str] = {t.name for t in registry.get_for_tenant(tenant_id)}

    # Intersection
    pruned: List[ToolMeta] = []
    for name in category_tool_names:
        if name in tenant_allowed:
            try:
                pruned.append(registry.get_by_name(name))
            except KeyError:
                log.warning("pruner: tool %r in category map but missing from registry", name)

    if not pruned:
        log.warning(
            "pruner: no tools found for category=%r tenant=%r — falling back to pdf_reader",
            category, tenant_id,
        )
        pruned = [registry.get_by_name("pdf_reader")]

    # Sort cheapest first so agents exhaust low-cost tools before expensive ones
    _cost_order = {"low": 0, "medium": 1, "high": 2}
    pruned.sort(key=lambda t: _cost_order.get(t.cost_tier, 99))

    log.info(
        "pruner: category=%r → %d tool(s): %s",
        category,
        len(pruned),
        [t.name for t in pruned],
    )
    return pruned


def prune_for_agent(agent_role: str, task: str, tenant_id: str) -> List[ToolMeta]:
    """
    Role-aware pruning — further restricts the tool list based on agent identity.

    the_reader  → document + retrieval tools only (no write or external verify).
    the_judge   → adds external verification (KYC/AML) but NO write tools.
    the_scribe  → only needs qdrant_evidence_search (reads evidence, writes report).

    Parameters
    ----------
    agent_role : 'reader' | 'judge' | 'scribe'
    task       : Natural-language task string.
    tenant_id  : Tenant identifier.
    """
    base_tools = prune_tools(task, tenant_id)

    READER_ALLOWED = {"ocr_unstructured", "ocr_textract", "pdf_reader", "qdrant_evidence_search"}
    JUDGE_ALLOWED  = READER_ALLOWED | {"kyc_opencorporates", "aml_sanctions_io", "web_search"}
    SCRIBE_ALLOWED = {"qdrant_evidence_search"}

    role_map = {
        "reader": READER_ALLOWED,
        "judge":  JUDGE_ALLOWED,
        "scribe": SCRIBE_ALLOWED,
    }

    allowed = role_map.get(agent_role, set(t.name for t in base_tools))
    filtered = [t for t in base_tools if t.name in allowed]

    if not filtered:
        log.warning(
            "prune_for_agent: role=%r left 0 tools — returning full pruned set",
            agent_role,
        )
        return base_tools

    log.info(
        "prune_for_agent: role=%r → %d tool(s): %s",
        agent_role,
        len(filtered),
        [t.name for t in filtered],
    )
    return filtered
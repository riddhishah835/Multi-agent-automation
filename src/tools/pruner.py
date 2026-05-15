# src/tools/pruner.py
import numpy as np
from typing import List
from src.tools.registry import registry, ToolMeta

# Hard cap from architecture rules — never give an agent more than 5 tools
MAX_TOOLS = 5


def _vectorize(text: str, vocab: List[str]) -> np.ndarray:
    words = set(text.lower().split())
    return np.array([1.0 if w in words else 0.0 for w in vocab])


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom > 0 else 0.0


def prune_tools(task_description: str, tenant_id: str, top_k: int = 3) -> List[ToolMeta]:
    """
    Return the top_k most relevant tools for this task and tenant.
    Never returns more than MAX_TOOLS regardless of what top_k is set to.
    """
    top_k = min(top_k, MAX_TOOLS)
    candidates = registry.get_for_tenant(tenant_id)
    if not candidates:
        return []

    all_text = " ".join(t.description for t in candidates) + " " + task_description
    vocab = list(set(all_text.lower().split()))
    task_vec = _vectorize(task_description, vocab)

    scored = [
        (_cosine(task_vec, _vectorize(t.description, vocab)), t)
        for t in candidates
    ]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [t for _, t in scored[:top_k]]
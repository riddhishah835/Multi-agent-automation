"""
Memory Layer — L1 hash cache (Redis / in-memory) + L2 semantic cache (Qdrant).
Part of Phase 3: Memory, State & Governance.

Responsibilities
----------------
* L1: exact-match lookup keyed on tenant_id + SHA-256(input + tool_signature)
* L2: semantic nearest-neighbour lookup in Qdrant (STRICTLY filtered by tenant_id)
* Falls back to pure Python dicts when Redis or Qdrant are unavailable.
* Emits correlated JSON trace entries for every cache event.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from typing import Any, Dict, Optional, Tuple

# ── optional heavy deps (graceful fallback) ──────────────────────────────────
try:
    import redis

    _redis_client: Optional[redis.Redis] = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=int(os.getenv("REDIS_DB", 0)),
        decode_responses=True,
        socket_connect_timeout=2,
    )
    _redis_client.ping()          # raises if not reachable
    _USE_REDIS = True
except Exception:
    _redis_client = None          
    _USE_REDIS = False

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, PointStruct, VectorParams, Filter, FieldCondition, MatchValue

    _qdrant = QdrantClient(
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", 6333)),
        timeout=5,
    )
    _USE_QDRANT = True
except Exception:
    _qdrant = None                
    _USE_QDRANT = False

try:
    from sentence_transformers import SentenceTransformer

    _embedder = SentenceTransformer(
        os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")
    )
    _USE_EMBED = True
except Exception:
    _embedder = None              
    _USE_EMBED = False

from src.memory.trace import TraceLogger

# ── constants ─────────────────────────────────────────────────────────────────
L1_TTL_SECONDS   = int(os.getenv("L1_TTL_SECONDS", 3600))   # 1 h
L2_COLLECTION    = os.getenv("QDRANT_COLLECTION", "agent_cache")
L2_SCORE_THRESH  = float(os.getenv("L2_SCORE_THRESH", 0.92))
VECTOR_DIM       = 384   # all-MiniLM-L6-v2 output dimension

_l1_fallback: Dict[str, Tuple[str, float]] = {}   # key → (value_json, expires_at)


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_cache_key(tenant_id: str, input_text: str, tool_signature: str) -> str:
    """Deterministic L1 key, strictly isolated by tenant."""
    raw = f"{input_text}||{tool_signature}"
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return f"{tenant_id}:{hashed}"


def _embed(text: str) -> Optional[list]:
    if _USE_EMBED and _embedder is not None:
        return _embedder.encode(text).tolist()
    return None


def _ensure_collection() -> None:
    """Create Qdrant collection if it doesn't exist yet."""
    if not _USE_QDRANT or _qdrant is None:
        return
    existing = {c.name for c in _qdrant.get_collections().collections}
    if L2_COLLECTION not in existing:
        _qdrant.recreate_collection(
            collection_name=L2_COLLECTION,
            vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
        )

_ensure_collection()


# ── L1 cache ──────────────────────────────────────────────────────────────────

def l1_get(cache_key: str, tenant_id: str, run_id: str) -> Optional[Any]:
    """Return cached value from Redis (or in-memory fallback)."""
    start = time.perf_counter()
    value = None
    logger = TraceLogger("memory.layer.l1", tenant_id=tenant_id, run_id=run_id)

    if _USE_REDIS and _redis_client is not None:
        raw = _redis_client.get(f"l1:{cache_key}")
        if raw:
            value = json.loads(raw)
    else:
        entry = _l1_fallback.get(cache_key)
        if entry and entry[1] > time.time():
            value = json.loads(entry[0])
        elif entry:
            _l1_fallback.pop(cache_key, None)

    logger.log_event(
        event="l1_get",
        cache_key=cache_key,
        hit=value is not None,
        latency_ms=round((time.perf_counter() - start) * 1000, 2),
        backend="redis" if _USE_REDIS else "dict",
    )
    return value


def l1_set(cache_key: str, value: Any, tenant_id: str, run_id: str) -> None:
    """Store a value in L1 with TTL."""
    logger = TraceLogger("memory.layer.l1", tenant_id=tenant_id, run_id=run_id)
    serialised = json.dumps(value)

    if _USE_REDIS and _redis_client is not None:
        _redis_client.setex(f"l1:{cache_key}", L1_TTL_SECONDS, serialised)
    else:
        _l1_fallback[cache_key] = (serialised, time.time() + L1_TTL_SECONDS)

    logger.log_event(event="l1_set", cache_key=cache_key, backend="redis" if _USE_REDIS else "dict")


# ── L2 cache (Qdrant) ─────────────────────────────────────────────────────────

def l2_get(input_text: str, tenant_id: str, run_id: str) -> Optional[Any]:
    """Semantic lookup; STRICTLY filtered by tenant_id."""
    if not _USE_QDRANT or not _USE_EMBED or _qdrant is None:
        return None

    start = time.perf_counter()
    logger = TraceLogger("memory.layer.l2", tenant_id=tenant_id, run_id=run_id)
    vector = _embed(input_text)
    
    # CRITICAL: Prevent cross-tenant data leakage
    tenant_filter = Filter(
        must=[FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))]
    )

    results = _qdrant.search(
        collection_name=L2_COLLECTION,
        query_vector=vector,
        query_filter=tenant_filter,
        limit=1,
        score_threshold=L2_SCORE_THRESH,
    )
    
    hit = bool(results)
    value = results[0].payload.get("output") if hit else None

    logger.log_event(
        event="l2_get",
        input_preview=input_text[:80],
        hit=hit,
        score=results[0].score if hit else None,
        latency_ms=round((time.perf_counter() - start) * 1000, 2),
    )
    return value


def l2_set(input_text: str, output: Any, tenant_id: str, run_id: str, metadata: Optional[Dict] = None) -> None:
    """Upsert an embedding + payload into Qdrant bound to a specific tenant."""
    if not _USE_QDRANT or not _USE_EMBED or _qdrant is None:
        return
        
    logger = TraceLogger("memory.layer.l2", tenant_id=tenant_id, run_id=run_id)
    vector = _embed(input_text)
    
    payload = {
        "tenant_id": tenant_id, 
        "input": input_text, 
        "output": output, 
        **(metadata or {})
    }
    
    # Generate a deterministic, tenant-isolated UUID
    point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{tenant_id}:{input_text}"))

    _qdrant.upsert(
        collection_name=L2_COLLECTION,
        points=[PointStruct(id=point_id, vector=vector, payload=payload)],
    )
    logger.log_event(event="l2_set", point_id=point_id, input_preview=input_text[:80])


# ── unified lookup / store ────────────────────────────────────────────────────

def cache_lookup(
    input_text: str, 
    tool_signature: str, 
    tenant_id: str, 
    run_id: str = "system"
) -> Tuple[Optional[Any], str]:
    """
    Try L1 first, then L2. Isolated by tenant.

    Returns
    -------
    (value, source)  where source ∈ {"l1", "l2", "miss"}
    """
    key = _make_cache_key(tenant_id, input_text, tool_signature)

    # 1. Check Exact Match
    result = l1_get(key, tenant_id, run_id)
    if result is not None:
        return result, "l1"

    # 2. Check Semantic Match
    result = l2_get(input_text, tenant_id, run_id)
    if result is not None:
        l1_set(key, result, tenant_id, run_id)   # Promote L2 hit to L1
        return result, "l2"

    return None, "miss"


def cache_store(
    input_text: str,
    tool_signature: str,
    output: Any,
    tenant_id: str,
    latency_ms: float,
    run_id: str = "system",
    metadata: Optional[Dict] = None,
) -> None:
    """Write a result to both L1 and L2, bound to the tenant."""
    key = _make_cache_key(tenant_id, input_text, tool_signature)
    meta = {"tool_signature": tool_signature, "latency_ms": latency_ms, **(metadata or {})}

    l1_set(key, output, tenant_id, run_id)
    l2_set(input_text, output, tenant_id, run_id, meta)

    logger = TraceLogger("memory.layer.store", tenant_id=tenant_id, run_id=run_id)
    logger.log_event(
        event="cache_store",
        cache_key=key,
        tool_signature=tool_signature,
        latency_ms=latency_ms,
    )
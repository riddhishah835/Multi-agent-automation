# src/tools/embedder.py
import numpy as np
from typing import List, Optional

# Try sentence-transformers first (best quality, local, free)
# Fallback to TF-IDF if not installed
try:
    from sentence_transformers import SentenceTransformer
    _model = SentenceTransformer("all-MiniLM-L6-v2")  # 80MB, downloads once
    EMBEDDER_BACKEND = "sentence_transformers"
except ImportError:
    from sklearn.feature_extraction.text import TfidfVectorizer
    _tfidf = TfidfVectorizer()
    _tfidf_fitted = False
    EMBEDDER_BACKEND = "tfidf"
    _model = None


def embed_text(text: str) -> List[float]:
    """
    Convert a text string into a semantic embedding vector.
    Uses sentence-transformers if available, TF-IDF as fallback.
    """
    if EMBEDDER_BACKEND == "sentence_transformers":
        vec = _model.encode(text, normalize_embeddings=True)
        return vec.tolist()
    else:
        return _tfidf_embed(text)


def embed_batch(texts: List[str]) -> List[List[float]]:
    """
    Embed multiple texts at once (faster than looping embed_text).
    """
    if EMBEDDER_BACKEND == "sentence_transformers":
        vecs = _model.encode(texts, normalize_embeddings=True, batch_size=32)
        return vecs.tolist()
    else:
        return [_tfidf_embed(t) for t in texts]


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """
    Cosine similarity between two embedding vectors.
    Returns a float between -1 and 1 (1 = identical meaning).
    """
    va = np.array(a)
    vb = np.array(b)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    return float(np.dot(va, vb) / denom) if denom > 0 else 0.0


def most_similar(
    query: str,
    candidates: List[str],
    top_k: int = 3
) -> List[tuple]:
    """
    Given a query string and a list of candidate strings,
    return the top_k most semantically similar candidates.

    Returns: List of (score, index, text) sorted by score descending.
    """
    if not candidates:
        return []

    query_vec = embed_text(query)
    candidate_vecs = embed_batch(candidates)

    scored = []
    for i, (text, vec) in enumerate(zip(candidates, candidate_vecs)):
        score = cosine_similarity(query_vec, vec)
        scored.append((score, i, text))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]


# ── TF-IDF fallback internals ────────────────────────────────────────────────

def _tfidf_embed(text: str) -> List[float]:
    """Fallback: simple TF-IDF vector when sentence-transformers not installed."""
    global _tfidf_fitted
    if not _tfidf_fitted:
        # Fit on a minimal corpus so it can transform any text
        _tfidf.fit([text, "compliance security encryption privacy vendor audit"])
        _tfidf_fitted = True
    try:
        vec = _tfidf.transform([text]).toarray()[0]
    except Exception:
        vec = np.zeros(10)
    return vec.tolist()
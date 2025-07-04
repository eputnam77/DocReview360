"""In-memory vector search used as a pgvector replacement."""

from __future__ import annotations

from collections import Counter
from math import sqrt
from typing import Dict, Iterable, List, Tuple

_vectors: Dict[str, List[float]] = {}


def _embed(text: str) -> List[float]:
    """Create a naive embedding vector from ``text``."""
    freq = Counter(text.lower().split())
    # 26 features based on first letter to keep dimensions small
    return [float(freq.get(chr(ord("a") + i), 0)) for i in range(26)]


def index_document(doc_id: str, content: str) -> None:
    """Store the embedding for ``content`` under ``doc_id``."""
    if not doc_id or not content:
        raise ValueError("doc_id and content are required")
    _vectors[doc_id] = _embed(content)


def _cosine(a: Iterable[float], b: Iterable[float]) -> float:
    """Return the cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    na = sqrt(sum(x * x for x in a))
    nb = sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def search(query: str, top_k: int = 5) -> List[Tuple[str, float]]:
    """Return ``top_k`` document ids ranked by cosine similarity."""
    if not query.strip():
        raise ValueError("query must not be empty")
    q_vec = _embed(query)
    scored = [(doc_id, _cosine(q_vec, vec)) for doc_id, vec in _vectors.items()]
    scored.sort(key=lambda t: t[1], reverse=True)
    return scored[:top_k]


def clear() -> None:
    """Remove all indexed vectors."""
    _vectors.clear()

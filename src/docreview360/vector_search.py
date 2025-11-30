"""Vector search helper with optional OpenSearch integration."""

from __future__ import annotations

import os
from collections import Counter, defaultdict
from math import isfinite, log, sqrt
from typing import Dict, Iterable, List, Tuple

import httpx

OPENSEARCH_URL = os.getenv("OPENSEARCH_URL")
PGVECTOR_URL = os.getenv("PGVECTOR_URL")

_vectors: Dict[str, Tuple[Counter[str], int]] = {}
_doc_freq: Dict[str, int] = defaultdict(int)
_total_docs = 0


def _embed(text: str) -> Counter[str]:
    """Return term frequency counter for ``text``.

    The previous implementation simply split on whitespace which meant tokens
    retained surrounding punctuation.  A document containing ``"world!"`` would
    therefore never match a search for ``"world"``.  Normalize tokens by
    extracting only alphanumeric word segments so punctuation is ignored and
    search queries behave more intuitively.
    """

    import re

    tokens = re.findall(r"\b\w+\b", text.lower())
    return Counter(tokens)


def index_document(doc_id: str, content: str) -> None:
    """Store the embedding for ``content`` under ``doc_id``.

    When ``OPENSEARCH_URL`` is defined the document is also indexed in
    OpenSearch. Any network failure raises ``RuntimeError`` so callers can
    decide whether to retry or fall back to the local index.
    """
    if (
        not isinstance(doc_id, str)
        or not doc_id.strip()
        or not isinstance(content, str)
        or not content
    ):
        raise ValueError("doc_id and content are required strings")
    global _total_docs
    tf = _embed(content)

    # If the document already exists, remove its previous contribution to
    # document frequencies so re-indexing keeps statistics accurate.
    if doc_id in _vectors:
        old_tf, _ = _vectors[doc_id]
        for term in old_tf:
            _doc_freq[term] -= 1
            if _doc_freq[term] <= 0:
                del _doc_freq[term]
    else:
        _total_docs += 1

    for term in tf:
        _doc_freq[term] += 1
    # ``len(content.split())`` counted tokens separated solely by whitespace and
    # misreported lengths for inputs like ``"foo-bar"`` which our tokenizer splits
    # into two words.  Store the length based on the tokenised representation so
    # the metadata remains consistent with the embedding.
    _vectors[doc_id] = (tf, sum(tf.values()))

    if OPENSEARCH_URL:
        try:
            httpx.put(
                f"{OPENSEARCH_URL.rstrip('/')}/documents/_doc/{doc_id}",
                json={"content": content},
                timeout=5,
            ).raise_for_status()
        except httpx.HTTPError as exc:
            raise RuntimeError("OpenSearch index failed") from exc

    if PGVECTOR_URL:
        try:
            httpx.post(
                f"{PGVECTOR_URL.rstrip('/')}/index",
                json={"id": doc_id, "content": content},
                timeout=5,
            ).raise_for_status()
        except httpx.HTTPError as exc:
            raise RuntimeError("pgvector index failed") from exc


def _cosine(a: Iterable[float], b: Iterable[float]) -> float:
    """Return the cosine similarity between two vectors.

    The previous implementation silently truncated the longer iterable when
    the vectors had different lengths because :func:`zip` stops at the
    shortest input. This produced incorrect scores and hid programming
    mistakes.  We now eagerly realize both iterables and validate that their
    lengths match, raising ``ValueError`` otherwise.
    """

    a_list = list(a)
    b_list = list(b)
    if len(a_list) != len(b_list):
        raise ValueError("vectors must be of equal length")
    # Guard against non-finite values.  ``math`` operations propagate NaNs and
    # infinities resulting in ``nan`` similarity scores which are difficult for
    # callers to handle.  Reject such inputs early with a clear error.
    for val in a_list + b_list:
        if not isfinite(val):
            raise ValueError("vectors must contain only finite numbers")
    dot = sum(x * y for x, y in zip(a_list, b_list))
    na = sqrt(sum(x * x for x in a_list))
    nb = sqrt(sum(y * y for y in b_list))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _tfidf_vector(tf: Counter[str]) -> List[float]:
    """Return a TF-IDF weighted vector for a term-frequency counter."""
    vector: List[float] = []
    for term in sorted(_doc_freq):
        tf_val = tf.get(term, 0)
        idf = log((_total_docs + 1) / (_doc_freq[term] + 1)) + 1
        vector.append(tf_val * idf)
    return vector


def search(query: str, top_k: int = 5) -> List[Tuple[str, float]]:
    """Return ``top_k`` document ids ranked by cosine similarity."""
    if not query.strip():
        raise ValueError("query must not be empty")
    if top_k <= 0:
        raise ValueError("top_k must be positive")

    if OPENSEARCH_URL:
        try:
            resp = httpx.post(
                f"{OPENSEARCH_URL.rstrip('/')}/_search",
                json={"query": query, "size": top_k},
                timeout=5,
            )
            resp.raise_for_status()
            hits = resp.json().get("hits", {}).get("hits", [])
            return [(hit["_id"], float(hit.get("_score", 0))) for hit in hits]
        except httpx.HTTPError as exc:
            raise RuntimeError("OpenSearch request failed") from exc

    elif PGVECTOR_URL:
        try:
            resp = httpx.post(
                f"{PGVECTOR_URL.rstrip('/')}/search",
                json={"query": query, "k": top_k},
                timeout=5,
            )
            resp.raise_for_status()
            hits = resp.json().get("results", [])
            return [(hit["id"], float(hit.get("score", 0))) for hit in hits]
        except httpx.HTTPError as exc:
            raise RuntimeError("pgvector search failed") from exc

    q_vec = _tfidf_vector(_embed(query))
    scored = []
    for doc_id, (tf, _) in _vectors.items():
        doc_vec = _tfidf_vector(tf)
        scored.append((doc_id, _cosine(q_vec, doc_vec)))
    scored.sort(key=lambda t: t[1], reverse=True)
    return scored[:top_k]


def clear() -> None:
    """Remove all indexed vectors and statistics."""
    _vectors.clear()
    _doc_freq.clear()
    global _total_docs
    _total_docs = 0

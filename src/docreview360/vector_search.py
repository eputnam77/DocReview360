"""Vector search helper with optional OpenSearch integration."""

from __future__ import annotations

import atexit
import os
import re
import threading
from collections import Counter, defaultdict
from math import isfinite, log, sqrt
from typing import Dict, Iterable, List, Tuple

import httpx

from docreview360 import http_client

OPENSEARCH_URL = os.getenv("OPENSEARCH_URL")
PGVECTOR_URL = os.getenv("PGVECTOR_URL")

_http_client = http_client.client(timeout=5)
atexit.register(_http_client.close)

_vectors: Dict[str, Tuple[Counter[str], int, List[float], float]] = {}
_doc_freq: Dict[str, int] = defaultdict(int)
_total_docs = 0
_dirty_tfidf = False
_tfidf_terms: List[str] = []
_tfidf_idf: List[float] = []
_TOKEN_PATTERN = re.compile(r"\b\w+\b")

# Guards all local-index mutations (_vectors, _doc_freq, _total_docs, TF-IDF state).
# Must be acquired before reading or writing any of those shared variables in a
# multithreaded Uvicorn/Gunicorn worker.
_vs_lock = threading.Lock()


def _embed(text: str) -> Counter[str]:
    """Return term frequency counter for ``text``.

    The previous implementation simply split on whitespace which meant tokens
    retained surrounding punctuation.  A document containing ``"world!"`` would
    therefore never match a search for ``"world"``.  Normalize tokens by
    extracting only alphanumeric word segments so punctuation is ignored and
    search queries behave more intuitively.
    """

    tokens = _TOKEN_PATTERN.findall(text.lower())
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
    tf = _embed(content)

    with _vs_lock:
        global _total_docs, _dirty_tfidf
        # If the document already exists, remove its previous contribution to
        # document frequencies so re-indexing keeps statistics accurate.
        if doc_id in _vectors:
            old_tf, _, _, _ = _vectors[doc_id]
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
        _vectors[doc_id] = (tf, sum(tf.values()), [], 0.0)
        _dirty_tfidf = True

    if OPENSEARCH_URL:
        try:
            _http_client.put(
                f"{OPENSEARCH_URL.rstrip('/')}/documents/_doc/{doc_id}",
                json={"content": content},
            ).raise_for_status()
        except httpx.HTTPError as exc:
            raise RuntimeError("OpenSearch index failed") from exc

    if PGVECTOR_URL:
        try:
            _http_client.post(
                f"{PGVECTOR_URL.rstrip('/')}/index",
                json={"id": doc_id, "content": content},
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


def _build_tfidf_vector(
    tf: Counter[str], terms: List[str], idf_values: List[float]
) -> List[float]:
    """Return a TF-IDF weighted vector aligned to ``terms``."""
    return [tf.get(term, 0) * idf_values[idx] for idx, term in enumerate(terms)]


def _refresh_tfidf_cache() -> None:
    """Recompute all TF-IDF vectors when document frequencies change."""
    global _dirty_tfidf, _tfidf_terms, _tfidf_idf
    _tfidf_terms = sorted(_doc_freq)
    _tfidf_idf = [
        log((_total_docs + 1) / (_doc_freq[term] + 1)) + 1
        for term in _tfidf_terms
    ]
    for doc_id, (tf, length, _, _) in _vectors.items():
        vector = _build_tfidf_vector(tf, _tfidf_terms, _tfidf_idf)
        norm = sqrt(sum(val * val for val in vector))
        _vectors[doc_id] = (tf, length, vector, norm)
    _dirty_tfidf = False


def _cosine_with_norms(
    a_vec: Iterable[float],
    a_norm: float,
    b_vec: Iterable[float],
    b_norm: float,
) -> float:
    """Return cosine similarity using precomputed norms."""
    a_list = list(a_vec)
    b_list = list(b_vec)
    if len(a_list) != len(b_list):
        raise ValueError("vectors must be of equal length")
    for val in a_list + b_list:
        if not isfinite(val):
            raise ValueError("vectors must contain only finite numbers")
    if not isfinite(a_norm) or not isfinite(b_norm):
        raise ValueError("vectors must contain only finite numbers")
    if a_norm == 0 or b_norm == 0:
        return 0.0
    dot = sum(x * y for x, y in zip(a_list, b_list))
    return dot / (a_norm * b_norm)


def search(query: str, top_k: int = 5) -> List[Tuple[str, float]]:
    """Return ``top_k`` document ids ranked by cosine similarity."""
    if not query.strip():
        raise ValueError("query must not be empty")
    if top_k <= 0:
        raise ValueError("top_k must be positive")

    if OPENSEARCH_URL:
        try:
            resp = _http_client.post(
                f"{OPENSEARCH_URL.rstrip('/')}/_search",
                json={"query": query, "size": top_k},
            )
            resp.raise_for_status()
            hits = resp.json().get("hits", {}).get("hits", [])
            return [(hit["_id"], float(hit.get("_score", 0))) for hit in hits]
        except httpx.HTTPError as exc:
            raise RuntimeError("OpenSearch request failed") from exc

    elif PGVECTOR_URL:
        try:
            resp = _http_client.post(
                f"{PGVECTOR_URL.rstrip('/')}/search",
                json={"query": query, "k": top_k},
            )
            resp.raise_for_status()
            hits = resp.json().get("results", [])
            return [(hit["id"], float(hit.get("score", 0))) for hit in hits]
        except httpx.HTTPError as exc:
            raise RuntimeError("pgvector search failed") from exc

    with _vs_lock:
        if _dirty_tfidf:
            _refresh_tfidf_cache()

        q_vec = _build_tfidf_vector(_embed(query), _tfidf_terms, _tfidf_idf)
        q_norm = sqrt(sum(val * val for val in q_vec))
        scored = []
        for doc_id, (_, _, doc_vec, doc_norm) in _vectors.items():
            scored.append((doc_id, _cosine_with_norms(q_vec, q_norm, doc_vec, doc_norm)))
    scored.sort(key=lambda t: t[1], reverse=True)
    return scored[:top_k]


def clear() -> None:
    """Remove all indexed vectors and statistics."""
    with _vs_lock:
        _vectors.clear()
        _doc_freq.clear()
        global _total_docs
        _total_docs = 0
        global _dirty_tfidf, _tfidf_terms, _tfidf_idf
        _dirty_tfidf = False
        _tfidf_terms = []
        _tfidf_idf = []

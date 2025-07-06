"""Celery application and example tasks."""

from __future__ import annotations

import os

import httpx
from celery import Celery

from .documents import documents
from .exporter import export_batch
from .search import search_index

broker_url = os.environ.get("CELERY_BROKER_URL", "memory://")
backend_url = os.environ.get("CELERY_RESULT_BACKEND", "cache+memory://")
app = Celery("docuflow", broker=broker_url, backend=backend_url)
app.conf.task_always_eager = os.environ.get("CELERY_EAGER", "1") == "1"


@app.task(name="docuflow.echo")
def echo(value: str) -> str:
    """Return ``value`` unchanged for testing purposes."""
    if not isinstance(value, str):
        raise ValueError("value must be a string")
    return value


@app.task(name="docuflow.word_count")
def word_count(text: str) -> int:
    """Return the number of words in ``text``."""
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    return len(text.split())


@app.task(name="docuflow.fetch_length")
def fetch_length(url: str) -> int:
    """Return the length of the response body from ``url``."""
    if not url.startswith(("http://", "https://")):
        raise ValueError("url must be http or https")
    resp = httpx.get(url, timeout=5)
    resp.raise_for_status()
    return len(resp.text)


@app.task(name="docuflow.quality_gate")
def quality_gate(text: str, weights: list[float] | None = None) -> float:
    """Return anomaly score for ``text`` using the provided model weights."""
    if weights is None:
        weights = [0.0, -0.1, 1.2, 0.0]
    from .wasm_plugin import lint_text

    passed = lint_text(text, weights)
    return 0.0 if passed else 1.0


@app.task(name="docuflow.export_documents")
def export_documents(doc_ids: list[str], fmt: str) -> bytes:
    """Return a ZIP archive for the specified document ids."""
    docs = []
    for doc_id in doc_ids:
        doc = documents.get(doc_id)
        if doc is None:
            raise KeyError(f"document '{doc_id}' not found")
        docs.append(doc)
    return export_batch(docs, fmt)


@app.task(name="docuflow.reindex_document")
def reindex_document(doc_id: str) -> None:
    """Reindex ``doc_id`` in the search index."""
    doc = documents.get(doc_id)
    if doc is None:
        raise KeyError(f"document '{doc_id}' not found")
    search_index.add_document(doc)

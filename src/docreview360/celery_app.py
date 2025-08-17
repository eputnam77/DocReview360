"""Celery application and example tasks."""

from __future__ import annotations

import os
from typing import Any, cast

import httpx
from celery import Celery, Task

from .backup_utils import create_backup
from .config import CONFIG_FILE, Config
from .documents import documents
from .exporter import export_batch
from .logs import TRACE_ID, log_event
from .search import search_index

broker_url = os.environ.get("CELERY_BROKER_URL", "memory://")
backend_url = os.environ.get("CELERY_RESULT_BACKEND", "cache+memory://")
app = Celery("docreview360", broker=broker_url, backend=backend_url)
app.conf.task_always_eager = os.environ.get("CELERY_EAGER", "1") == "1"


class TracedTask(Task):
    """Task that propagates ``TRACE_ID`` and logs lifecycle events."""

    def apply_async(self, *args: Any, **kwargs: Any) -> Any:
        trace_id = TRACE_ID.get(None)
        headers = kwargs.setdefault("headers", {})
        if trace_id:
            headers.setdefault("trace_id", trace_id)
        return super().apply_async(*args, **kwargs)

    def __call__(self, *args: Any, **kwargs: Any):
        trace_id = getattr(getattr(self, "request", None), "headers", {}).get("trace_id")
        if trace_id:
            TRACE_ID.set(trace_id)
        log_event("task_started", task=self.name)
        try:
            result = self.run(*args, **kwargs)
            log_event("task_succeeded", task=self.name)
            return result
        except Exception as exc:  # pragma: no cover - defensive
            log_event("task_failed", task=self.name, error=str(exc), severity="error")
            raise


app.Task = TracedTask


def echo(value: str) -> str:
    """Return ``value`` unchanged for testing purposes."""
    if not isinstance(value, str):
        raise ValueError("value must be a string")
    return value


echo = cast(Task, app.task(name="docreview360.echo")(echo))


def word_count(text: str) -> int:
    """Return the number of words in ``text``."""
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    return len(text.split())


word_count = cast(Task, app.task(name="docreview360.word_count")(word_count))


def fetch_length(url: str) -> int:
    """Return the length of the response body from ``url``."""
    if not url.startswith(("http://", "https://")):
        raise ValueError("url must be http or https")
    resp = httpx.get(url, timeout=5)
    resp.raise_for_status()
    return len(resp.text)


fetch_length = cast(Task, app.task(name="docreview360.fetch_length")(fetch_length))


def quality_gate(text: str, weights: list[float] | None = None) -> float:
    """Return anomaly score for ``text`` using the provided model weights."""
    if weights is None:
        weights = [0.0, -0.1, 1.2, 0.0]
    from .wasm_plugin import lint_text

    passed = lint_text(text, weights)
    return 0.0 if passed else 1.0


quality_gate = cast(Task, app.task(name="docreview360.quality_gate")(quality_gate))


def export_documents(doc_ids: list[str], fmt: str) -> bytes:
    """Return a ZIP archive for ``doc_ids`` in the given format.

    Parameters
    ----------
    doc_ids:
        Document identifiers to export.
    fmt:
        Target format supported by :func:`export_batch`.
    """

    if not doc_ids:
        raise ValueError("no document ids provided")

    docs = []
    for doc_id in doc_ids:
        doc = documents.get(doc_id)
        if doc is None:
            raise KeyError(f"document '{doc_id}' not found")
        docs.append(doc)

    cfg = Config.load(CONFIG_FILE)
    template = cfg.filename_template if cfg else "{id}"
    return export_batch(docs, fmt, name_template=template)


export_documents = cast(Task, app.task(name="docreview360.export_documents")(export_documents))


def reindex_document(doc_id: str) -> None:
    """Reindex ``doc_id`` in the search index."""

    if not doc_id:
        raise ValueError("doc_id required")

    doc = documents.get(doc_id)
    if doc is None:
        raise KeyError(f"document '{doc_id}' not found")
    search_index.add_document(doc)


reindex_document = cast(Task, app.task(name="docreview360.reindex_document")(reindex_document))


def create_backup_task(path: str) -> str:
    """Create a compressed backup at ``path`` and return the location."""

    if not path:
        raise ValueError("path required")

    target = create_backup(path)
    return str(target)


create_backup_task = cast(Task, app.task(name="docreview360.create_backup")(create_backup_task))


def reindex_all() -> int:
    """Reindex all known documents and return the number processed."""

    count = 0
    for doc in documents.values():
        search_index.add_document(doc)
        count += 1
    return count


reindex_all = cast(Task, app.task(name="docreview360.reindex_all")(reindex_all))

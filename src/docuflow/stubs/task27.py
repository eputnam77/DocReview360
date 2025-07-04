"""Batch export helper for task 27."""

from typing import Iterable

from ..documents import DocumentModel
from ..exporter import export_batch, preview_document
from . import record_task_completion


def task27(docs: Iterable[DocumentModel], fmt: str) -> bytes:
    """Return a ZIP archive containing the exported documents."""
    result = export_batch(docs, fmt)
    record_task_completion(27)
    return result


def task27_preview(doc: DocumentModel, fmt: str, length: int = 30) -> str:
    """Return a short preview of a document export."""
    snippet = preview_document(doc, fmt, length=length)
    record_task_completion(27)
    return snippet

"""Documenso signature integration stub."""

from __future__ import annotations

from . import record_task_completion


def sign_document(doc_id: str, user: str) -> str:
    """Return a pseudo signature string."""
    record_task_completion(80)
    return f"signature:{doc_id}:{user}"

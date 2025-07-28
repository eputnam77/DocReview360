"""Persistent document store placeholder."""

from __future__ import annotations

from sqlalchemy.orm import Session

from ..stubs import record_task_completion


def save_document(session: Session, doc_id: str, content: str) -> bool:
    """Persist document edit and version history."""
    record_task_completion(251)
    raise NotImplementedError

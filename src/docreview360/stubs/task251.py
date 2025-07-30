"""Persistent document store placeholder."""

from __future__ import annotations

from sqlalchemy.orm import Session

from ..stubs import record_task_completion


def save_document(session: Session, doc_id: str, content: str) -> bool:
    """Persist document edit and version history."""
    from sqlalchemy import text

    record_task_completion(251)

    # check if document exists
    result = session.execute(
        text("SELECT content FROM documents WHERE id=:id"),
        {"id": doc_id},
    ).fetchone()
    if result is None:
        session.execute(
            text("INSERT INTO documents (id, project_id, content) VALUES (:id, 0, :content)"),
            {"id": doc_id, "content": content},
        )
        return True

    session.execute(
        text("INSERT INTO document_versions (document_id, content) VALUES (:id, :prev)"),
        {"id": doc_id, "prev": result[0]},
    )
    session.execute(
        text("UPDATE documents SET content=:content WHERE id=:id"),
        {"content": content, "id": doc_id},
    )
    return True

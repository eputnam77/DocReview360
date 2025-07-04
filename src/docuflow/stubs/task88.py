"""Simple GraphQL query handler."""

from __future__ import annotations

from . import record_task_completion


def execute_query(query: str) -> dict[str, object]:
    """Return canned data based on the ``query`` string."""
    record_task_completion(88)
    if "projects" in query:
        return {"projects": [{"id": 1, "name": "demo"}]}
    if "documents" in query:
        return {"documents": [{"id": 2, "title": "doc"}]}
    return {"ping": "pong"}

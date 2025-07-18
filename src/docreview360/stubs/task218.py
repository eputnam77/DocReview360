"""RBAC helper for writer review permissions (Task 218)."""

from __future__ import annotations

from ..stubs import record_task_completion


def send_for_review(role: str, document_id: str) -> bool:
    """Return ``True`` when writers may send documents for review."""
    record_task_completion(218)
    raise NotImplementedError("task 218 not implemented")

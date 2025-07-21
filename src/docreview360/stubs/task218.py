"""RBAC helper for writer review permissions (Task 218)."""

from __future__ import annotations

from ..stubs import record_task_completion

ALLOWED_ROLES = {"writer", "project_lead"}


def send_for_review(role: str, document_id: str) -> bool:
    """Return ``True`` when the ``role`` may send ``document_id`` for review."""

    if not role or not document_id:
        raise ValueError("role and document_id required")

    record_task_completion(218)
    return role in ALLOWED_ROLES

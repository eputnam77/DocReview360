"""Approval comment notification helper."""

from __future__ import annotations

from ..stubs import record_task_completion


def task210(owner: str, comment: str) -> str:
    """Return a notification message."""

    record_task_completion(210)
    return f"Notify {owner}: {comment}"

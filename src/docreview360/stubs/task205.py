"""Approval comment editing helper."""

from __future__ import annotations

from ..stubs import record_task_completion


def task205(comment: str, new_text: str) -> str:
    """Return the updated comment text."""

    record_task_completion(205)
    return new_text

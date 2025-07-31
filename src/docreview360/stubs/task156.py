"""Implementation for task 156."""

from __future__ import annotations

from . import record_task_completion


def task156(comments: list[str]) -> list[str]:
    """Return comments appended with a thumbs-up reaction."""
    record_task_completion(156)
    return [f"{c} :+1:" for c in comments]

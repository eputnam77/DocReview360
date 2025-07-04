"""Implementation for task 80."""

from . import record_task_completion


def task80() -> None:
    """Mark task 80 as completed for logging."""
    record_task_completion(int("80"))
    return None

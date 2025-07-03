"""Helper utilities for stub task modules."""

from __future__ import annotations

from ..logs import log_event

def record_task_completion(task_id: int) -> None:
    """Log completion of a stub task.

    Parameters
    ----------
    task_id:
        Identifier of the task being executed.
    """
    log_event(f"task_{task_id}_completed")


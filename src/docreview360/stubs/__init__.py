"""Helper utilities for stub task modules."""

from __future__ import annotations


def record_task_completion(task_id: int) -> None:
    """Log completion of a stub task.

    The stub modules used in the kata have no real logging backend available.
    Historically this function called :func:`docreview360.logs.log_event` which
    attempted to initialize the full database logging stack.  Importing or
    invoking the stubs in isolation therefore triggered ``sqlalchemy`` errors
    when the database was not configured, causing otherwise harmless helper
    functions to fail.

    Logging here is best‑effort; if the logging system is unavailable the stub
    should still complete silently so tests focusing on functional behavior can
    run.  Any exception from ``log_event`` is suppressed.

    Parameters
    ----------
    task_id:
        Identifier of the task being executed.
    """
    try:
        from ..logs import log_event
    except Exception:
        return

    try:
        log_event("task_completed", entity_id=str(task_id))
    except Exception:
        # Logging is optional for stubs; failures should not break tests.
        pass

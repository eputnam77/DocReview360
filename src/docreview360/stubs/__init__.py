"""Helper utilities for stub task modules."""

from __future__ import annotations

from typing import Callable, Optional

LogEventFunc = Callable[..., None]


def _resolve_log_event() -> Optional[LogEventFunc]:
    """Resolve :func:`docreview360.logs.log_event` without crashing imports.

    The real logging stack performs SQL initialisation.  Importing it during
    tests that exercise stubs in isolation previously exploded with database
    configuration errors.  Resolving the callable lazily lets us expose a
    module-level attribute for monkeypatching while still tolerating missing
    infrastructure.
    """

    try:  # pragma: no cover - exercised indirectly via ``log_event`` wrapper.
        from ..logs import log_event as resolved
    except Exception:  # pragma: no cover - defensive for optional dependency.
        return None
    return resolved


_LOG_EVENT: Optional[LogEventFunc] = _resolve_log_event()


def log_event(*args, **kwargs) -> None:
    """Best-effort proxy to the real logging hook.

    Exposed so tests can monkeypatch ``docreview360.stubs.log_event`` directly,
    matching the behaviour that ``record_task_completion`` expects.
    """

    if _LOG_EVENT is None:
        raise RuntimeError("Logging backend unavailable")
    _LOG_EVENT(*args, **kwargs)


def record_task_completion(task_id: int) -> None:
    """Log completion of a stub task.

    Parameters
    ----------
    task_id:
        Identifier of the task being executed.
    """

    try:
        log_event("task_completed", entity_id=str(task_id))
    except Exception:
        # Logging is optional for stubs; failures should not break tests.
        pass

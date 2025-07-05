"""Log alert rule helper for task 75."""

from __future__ import annotations

from typing import Callable

from ..logs import LogEntry, register_alert
from . import record_task_completion


def register_log_alert(pattern: str, callback: Callable[[LogEntry], None]) -> None:
    """Register ``callback`` to run when a log action contains ``pattern``."""

    if not pattern:
        raise ValueError("pattern required")
    register_alert(pattern, callback)
    record_task_completion(75)

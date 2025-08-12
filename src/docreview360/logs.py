"""Simple asynchronous audit log utilities."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

pydantic_dataclass: Callable[..., Any]
try:  # pragma: no cover - optional pydantic dataclass integration
    from pydantic.dataclasses import dataclass as pydantic_dataclass
except Exception:  # pragma: no cover - pydantic is absent
    pydantic_dataclass = dataclass


@pydantic_dataclass
class LogEntry:
    """Structured log entry used for audit logs."""

    timestamp: datetime
    action: str
    user: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def model_dump(
        self, *args: Any, **kwargs: Any
    ) -> Dict[str, Any]:  # pragma: no cover - compatibility
        return {
            "timestamp": self.timestamp,
            "action": self.action,
            "user": self.user,
            "metadata": self.metadata,
        }


logs: List[LogEntry] = []
alerts: List[tuple[str, Callable[[LogEntry], None]]] = []
_listeners: List[Callable[[LogEntry], None]] = []


async def log_stream() -> AsyncIterator[LogEntry]:
    """Yield log entries as they are recorded."""

    queue: asyncio.Queue[LogEntry] = asyncio.Queue()

    def _enqueue(entry: LogEntry) -> None:
        queue.put_nowait(entry)

    register_listener(_enqueue)
    try:
        while True:
            entry = await queue.get()
            yield entry
    finally:
        unregister_listener(_enqueue)


def register_alert(pattern: str, callback: Callable[[LogEntry], None]) -> None:
    """Register an alert callback triggered when action contains pattern."""
    alerts.append((pattern, callback))


def register_listener(callback: Callable[[LogEntry], None]) -> None:
    """Subscribe to live log events."""
    _listeners.append(callback)


def unregister_listener(callback: Callable[[LogEntry], None]) -> None:
    """Remove a previously registered listener."""
    if callback in _listeners:
        _listeners.remove(callback)


def log_event(action: str, user: str | None = None, **metadata: Any) -> LogEntry:
    """Record a log entry and return it."""
    entry = LogEntry(
        timestamp=datetime.now(timezone.utc),
        action=action,
        user=user,
        metadata=metadata,
    )  # type: ignore[call-arg]
    logs.append(entry)
    for pattern, cb in alerts:
        if pattern in action:
            cb(entry)
    for listener in list(_listeners):
        listener(entry)
    return entry


def query_logs(action: str | None = None, user: str | None = None) -> List[LogEntry]:
    """Return logs filtered by optional action and user."""
    results = logs
    if action is not None:
        results = [e for e in results if e.action == action]
    if user is not None:
        results = [e for e in results if e.user == user]
    return results


def export_logs() -> List[LogEntry]:
    """Return all logs for export purposes."""
    return list(logs)


def clear_logs() -> None:
    """Remove all stored logs (useful for tests)."""
    logs.clear()


async def watch_logs(callback: Callable[[LogEntry], None]) -> None:
    """Invoke ``callback`` for each new log entry.

    This helper provides a minimal real-time log viewer suitable for
    CLI tools or simple dashboards. It relies on ``log_stream`` and
    ensures the callback is only executed while the consumer awaits
    events. Usage example::

        async def printer(entry: LogEntry) -> None:
            print(entry.action)

        await watch_logs(printer)
    """

    async for entry in log_stream():
        try:
            callback(entry)
        except Exception:  # pragma: no cover - defensive
            pass

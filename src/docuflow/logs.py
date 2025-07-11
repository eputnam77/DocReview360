from __future__ import annotations

from datetime import datetime
from typing import Any, AsyncIterator, Callable, Dict, List, Optional
import asyncio

from pydantic import BaseModel


class LogEntry(BaseModel):
    """Structured log entry."""

    timestamp: datetime
    action: str
    user: Optional[str] = None
    metadata: Dict[str, Any] = {}


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
    entry = LogEntry(timestamp=datetime.utcnow(), action=action, user=user, metadata=metadata)
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

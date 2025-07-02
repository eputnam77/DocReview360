from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class LogEntry(BaseModel):
    """Structured log entry."""

    timestamp: datetime
    action: str
    user: Optional[str] = None
    metadata: Dict[str, Any] = {}


logs: List[LogEntry] = []


def log_event(action: str, user: str | None = None, **metadata: Any) -> LogEntry:
    """Record a log entry and return it."""
    entry = LogEntry(timestamp=datetime.utcnow(), action=action, user=user, metadata=metadata)
    logs.append(entry)
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

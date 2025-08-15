"""Simple asynchronous audit log utilities."""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Callable, Dict, List

from sqlalchemy import delete, insert, select

from .database import Database, default_url
from .models import AuditLog

try:  # pragma: no cover - pydantic optional
    from pydantic import BaseModel, Field
except Exception:  # pragma: no cover

    class BaseModel:  # type: ignore[no-redef]
        """Fallback stub when Pydantic is unavailable."""

        def __init__(self, **data: Any) -> None:  # pragma: no cover - simple shim
            for k, v in data.items():
                setattr(self, k, v)

        def model_dump(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:  # pragma: no cover
            return self.__dict__


class LogEntry(BaseModel):
    """Audit log entry returned by API endpoints."""

    id: str
    timestamp: datetime = Field()
    user_id: str | None = None
    action: str
    entity_id: str | None = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    severity: str = "info"
    ip_address: str | None = None

    # Backwards compatibility aliases -------------------------------------
    @property
    def actor(self) -> str | None:  # pragma: no cover - simple accessor
        return self.user_id

    @property
    def context(self) -> Dict[str, Any]:  # pragma: no cover - simple accessor
        return self.metadata

    @property
    def details(self) -> Dict[str, Any]:  # pragma: no cover - simple accessor
        return self.metadata


class _LogList(list[LogEntry]):
    """In-memory mirror of log entries that also clears the database."""

    def clear(self) -> None:  # pragma: no cover - thin wrapper
        super().clear()
        try:
            db = _get_db()
        except Exception:
            return
        with db.session() as conn:
            conn.execute(delete(AuditLog))


logs: _LogList = _LogList()
alerts: List[tuple[str, Callable[[LogEntry], None]]] = []
_listeners: List[Callable[[LogEntry], None]] = []


_db: Database | None = None


def _get_db() -> Database:
    """Return a lazily initialized :class:`Database` instance."""

    global _db
    if _db is None:
        url = os.getenv("DOCREVIEW360_DATABASE_URL", default_url("sqlite"))
        _db = Database(url)
        _db.migrate()
    return _db


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


def log_event(
    action: str,
    actor: str | None = None,
    *,
    entity_id: str | None = None,
    severity: str = "info",
    ip: str | None = None,
    **context: Any,
) -> LogEntry:
    """Record a log entry in the database and return it."""

    entry = LogEntry(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc),
        user_id=actor,
        action=action,
        entity_id=entity_id or context.pop("entity_id", None),
        metadata=context,
        severity=severity,
        ip_address=ip or context.get("ip_address") or context.get("ip"),
    )
    db = _get_db()
    with db.session() as conn:
        import json

        conn.execute(
            insert(AuditLog).values(
                id=entry.id,
                timestamp=entry.timestamp,
                user_id=entry.user_id,
                action=entry.action,
                entity_id=entry.entity_id,
                details=json.dumps(entry.metadata),
                severity=entry.severity,
                ip_address=entry.ip_address,
            )
        )
    logs.append(entry)
    for pattern, cb in alerts:
        if pattern in action:
            cb(entry)
    for listener in list(_listeners):
        listener(entry)
    return entry


def log_verification_failure(actor: str, ip: str, **context: Any) -> LogEntry:
    """Log a failed signature verification with ``actor`` and client ``ip``."""

    return log_event(
        "signature_verification_failed",
        actor=actor,
        ip=ip,
        **context,
    )


def query_logs(action: str | None = None, actor: str | None = None) -> List[LogEntry]:
    """Return logs filtered by optional action and actor."""

    db = _get_db()
    stmt = select(AuditLog)
    if action is not None:
        stmt = stmt.where(AuditLog.action == action)
    if actor is not None:
        stmt = stmt.where(AuditLog.user_id == actor)
    with db.session() as conn:
        rows = conn.execute(stmt).all()
    return [
        LogEntry(
            id=row.id,
            timestamp=row.timestamp,
            user_id=row.user_id,
            action=row.action,
            entity_id=row.entity_id,
            metadata=_coerce_details(row.details),
            severity=row.severity,
            ip_address=row.ip_address,
        )
        for row in rows
    ]


def _coerce_details(value: Any) -> Dict[str, Any]:
    """Return ``value`` as a dictionary, parsing JSON strings if needed."""

    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            import json
            return json.loads(value)  # type: ignore[no-any-return]
        except Exception:  # pragma: no cover - fallback for invalid JSON
            return {}
    return {}


def export_logs() -> List[LogEntry]:
    """Return all logs for export purposes."""
    return query_logs()


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
        except Exception:
            pass

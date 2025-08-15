"""Simple asynchronous audit log utilities."""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone
from functools import wraps
from typing import Any, AsyncIterator, Callable, Dict, List, TypeVar, cast, get_type_hints

from sqlalchemy import delete, insert, select

from .database import Database, default_url
from .models import AuditLog, AuditLogRecord

LogEntry = AuditLogRecord


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
    user_id: str | None = None,
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
        user_id=user_id,
        action=action,
        entity_id=entity_id or context.pop("entity_id", None),
        details=context,
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
                details=json.dumps(entry.details),
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


def log_verification_failure(user_id: str, ip: str, **context: Any) -> LogEntry:
    """Log a failed signature verification with ``user_id`` and client ``ip``."""

    return log_event(
        "signature_verification_failed",
        user_id=user_id,
        ip=ip,
        **context,
    )


def query_logs(
    action: str | None = None,
    user_id: str | None = None,
    log_id: str | None = None,
) -> List[LogEntry]:
    """Return logs filtered by optional action, user, or id sorted by timestamp."""

    db = _get_db()
    stmt = select(AuditLog)
    if action is not None:
        stmt = stmt.where(AuditLog.action == action)
    if user_id is not None:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if log_id is not None:
        stmt = stmt.where(AuditLog.id == log_id)
    stmt = stmt.order_by(AuditLog.timestamp)
    with db.session() as conn:
        rows = conn.execute(stmt).all()
    return [
        LogEntry(
            id=row.id,
            timestamp=row.timestamp,
            user_id=row.user_id,
            action=row.action,
            entity_id=row.entity_id,
            details=_coerce_details(row.details),
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


F = TypeVar("F", bound=Callable[..., Any])


def log_call(func: F | None = None, *, enabled: bool = True) -> F:  # type: ignore[override]
    """Decorator that logs function calls and outcomes via :func:`log_event`.

    The wrapped function accepts an ``audit`` keyword-only flag to opt out of
    logging when set to ``False``. The decorator attempts to determine a
    ``user_id`` from common parameter names such as ``current_user``, ``user`` or
    ``x_user``. For FastAPI handlers it also checks the ``Request`` object for an
    ``X-User`` header. All parameters and the resulting outcome (or exception) are
    forwarded as ``context`` to :func:`log_event`.
    """

    def decorator(f: F) -> F:
        is_coro = asyncio.iscoroutinefunction(f)

        @wraps(f)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            audit = kwargs.pop("audit", enabled)
            if not audit:
                return await f(*args, **kwargs)

            user = (
                kwargs.get("current_user")
                or kwargs.get("user")
                or kwargs.get("x_user")
            )
            if user is None and (request := kwargs.get("request")) is not None:
                try:
                    user = request.headers.get("x-user") or request.headers.get("X-User")
                except Exception:  # pragma: no cover - defensive
                    user = None
            user_id = getattr(user, "username", None) or getattr(user, "id", None)
            if user_id is None and user is not None:
                user_id = str(user)

            args_repr = [repr(a) for a in args]
            kwargs_repr = {k: repr(v) for k, v in kwargs.items()}
            try:
                result = await f(*args, **kwargs)
                log_event(
                    f.__name__,
                    user_id=user_id,
                    outcome="success",
                    args=args_repr,
                    kwargs=kwargs_repr,
                    result=repr(result),
                )
                return result
            except Exception as exc:
                log_event(
                    f.__name__,
                    user_id=user_id,
                    outcome="error",
                    args=args_repr,
                    kwargs=kwargs_repr,
                    error=str(exc),
                )
                raise

        @wraps(f)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            audit = kwargs.pop("audit", enabled)
            if not audit:
                return f(*args, **kwargs)

            user = (
                kwargs.get("current_user")
                or kwargs.get("user")
                or kwargs.get("x_user")
            )
            if user is None and (request := kwargs.get("request")) is not None:
                try:
                    user = request.headers.get("x-user") or request.headers.get("X-User")
                except Exception:  # pragma: no cover - defensive
                    user = None
            user_id = getattr(user, "username", None) or getattr(user, "id", None)
            if user_id is None and user is not None:
                user_id = str(user)

            args_repr = [repr(a) for a in args]
            kwargs_repr = {k: repr(v) for k, v in kwargs.items()}
            try:
                result = f(*args, **kwargs)
                log_event(
                    f.__name__,
                    user_id=user_id,
                    outcome="success",
                    args=args_repr,
                    kwargs=kwargs_repr,
                    result=repr(result),
                )
                return result
            except Exception as exc:
                log_event(
                    f.__name__,
                    user_id=user_id,
                    outcome="error",
                    args=args_repr,
                    kwargs=kwargs_repr,
                    error=str(exc),
                )
                raise

        annotations = get_type_hints(f)
        async_wrapper.__annotations__ = annotations
        sync_wrapper.__annotations__ = annotations
        async_wrapper.__globals__.update(f.__globals__)
        sync_wrapper.__globals__.update(f.__globals__)
        return cast(F, async_wrapper if is_coro else sync_wrapper)

    if func is None:
        return cast(F, decorator)  # type: ignore[return-value]
    return decorator(func)

# SPDX-License-Identifier: MIT
"""Event dispatching functions for the audit log."""

from __future__ import annotations

import asyncio
import hashlib
import traceback
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, AsyncIterator, Callable, Dict, Literal, TypeVar, cast, get_type_hints

from sqlalchemy import insert, select

from .. import log_connectors
from ..models import AuditLog, LogEntry
from ._db import (
    TRACE_ID,
    _emit_structured_runtime_log,
    _get_db,
    _listeners,
    _normalize_error_code,
    _normalize_severity,
    _redact,
    alerts,
    logs,
)

F = TypeVar("F", bound=Callable[..., Any])


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
    entity_type: str | None = None,
    severity: Literal["info", "warning", "error"] = "info",
    ip: str | None = None,
    trace_id: str | None = None,
    document_hash: str | None = None,
    provider_response: Dict[str, Any] | None = None,
    **context: Any,
) -> LogEntry:
    """Record a log entry in the database and return it."""

    normalized_severity = _normalize_severity(str(severity))
    sanitized_context = cast(dict[str, Any], _redact(context))
    trace = trace_id or TRACE_ID.get(None)
    if trace:
        sanitized_context.setdefault("trace_id", trace)
    if document_hash is None:
        document_hash = sanitized_context.pop("document_hash", None)
    if provider_response is None:
        provider_response = sanitized_context.pop("provider_response", None)
    provider_payload: dict[str, Any]
    if isinstance(provider_response, dict):
        provider_payload = cast(dict[str, Any], _redact(provider_response))
    elif provider_response is None:
        provider_payload = {}
    else:
        provider_payload = {"value": _redact(provider_response)}

    error_code = _normalize_error_code(sanitized_context.get("error_code"))
    if normalized_severity == "error" and error_code is None:
        error_code = "system_error"
    if error_code is not None:
        sanitized_context["error_code"] = error_code

    timestamp = datetime.now(timezone.utc).isoformat()
    db = _get_db()
    with db.session() as conn:
        prev_hash = conn.execute(
            select(AuditLog.hash).order_by(AuditLog.timestamp.desc()).limit(1)
        ).scalar_one_or_none()
    data = {
        "id": str(uuid.uuid4()),
        "timestamp": timestamp,
        "user_id": user_id,
        "action": action,
        "entity_type": entity_type or sanitized_context.pop("entity_type", None),
        "entity_id": entity_id or sanitized_context.pop("entity_id", None),
        "details": sanitized_context,
        "severity": normalized_severity,
        "ip_address": ip or sanitized_context.get("ip_address") or sanitized_context.get("ip"),
        "prev_hash": prev_hash,
        "document_hash": document_hash,
        "provider_response": provider_payload,
    }
    import json

    payload = json.dumps(
        {k: v for k, v in data.items() if k != "hash"}, sort_keys=True, default=str
    ).encode()
    prev_bytes = bytes.fromhex(prev_hash) if prev_hash else b""
    data["hash"] = hashlib.sha256(prev_bytes + payload).hexdigest()
    entry = LogEntry.model_validate(data)
    with db.session() as conn:
        conn.execute(
            insert(AuditLog).values(
                id=entry.id,
                timestamp=entry.timestamp,
                user_id=entry.user_id,
                action=entry.action,
                entity_type=entry.entity_type,
                entity_id=entry.entity_id,
                details=json.dumps(entry.details),
                severity=entry.severity,
                ip_address=entry.ip_address,
                prev_hash=entry.prev_hash,
                hash=entry.hash,
                document_hash=entry.document_hash,
                provider_response=json.dumps(entry.provider_response),
            )
        )
    logs.append(entry)
    _emit_structured_runtime_log(entry)
    for pattern, cb in alerts:
        if pattern in action:
            cb(entry)
    for listener in list(_listeners):
        listener(entry)
    if log_connectors.connectors:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(log_connectors.emit(entry))
        else:
            loop.create_task(log_connectors.emit(entry))
    return entry


def log_verification_failure(user_id: str, ip: str, **context: Any) -> LogEntry:
    """Log a failed signature verification with ``user_id`` and client ``ip``."""

    return log_event(
        "signature_verification_failed",
        user_id=user_id,
        ip=ip,
        **context,
    )


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


async def watch_logs(callback: Callable[[LogEntry], None]) -> None:
    """Invoke ``callback`` for each new log entry."""

    async for entry in log_stream():
        try:
            callback(entry)
        except Exception:
            pass


def schedule_log_purge() -> None:
    """Configure periodic purging of expired operational logs."""

    from docreview360.celery_app import app
    from docreview360.settings_manager import load_settings
    from ._db import LOG_RETENTION_DAYS
    from ._query import purge_expired_logs

    settings = load_settings()
    cfg = settings.get("logs", {})
    try:
        retention = int(cfg.get("retention_days", LOG_RETENTION_DAYS))
    except (TypeError, ValueError):
        retention = LOG_RETENTION_DAYS
    if retention <= 0:
        retention = LOG_RETENTION_DAYS
    try:
        interval = int(cfg.get("purge_interval_minutes", 60 * 24))
    except (TypeError, ValueError):
        interval = 60 * 24
    if interval <= 0:
        interval = 60 * 24
    app.task(name="docreview360.purge_expired_logs")(purge_expired_logs)
    app.conf.beat_schedule = app.conf.get("beat_schedule", {})
    app.conf.beat_schedule["purge_expired_logs"] = {
        "task": "docreview360.purge_expired_logs",
        "schedule": timedelta(minutes=interval),
        "args": (retention,),
    }


def log_call(func: F | None = None, *, enabled: bool = True) -> F:  # noqa: C901
    """Decorator that logs function calls and outcomes via :func:`log_event`."""

    def decorator(f: F) -> F:  # noqa: C901
        is_coro = asyncio.iscoroutinefunction(f)

        @wraps(f)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            audit = kwargs.pop("audit", enabled)
            if not audit:
                return await f(*args, **kwargs)

            user = kwargs.get("current_user") or kwargs.get("user") or kwargs.get("x_user")
            if user is None and (request := kwargs.get("request")) is not None:
                try:
                    user = request.headers.get("x-user") or request.headers.get("X-User")
                except Exception:  # pragma: no cover - defensive
                    user = None
            user_id = getattr(user, "username", None) or getattr(user, "id", None)
            if user_id is None and user is not None:
                user_id = str(user)

            args_repr = [repr(_redact(a)) for a in args]
            kwargs_repr = {k: repr(_redact(v, k)) for k, v in kwargs.items()}
            try:
                result = await f(*args, **kwargs)
                log_event(
                    f.__name__,
                    user_id=user_id,
                    outcome="success",
                    severity="info",
                    args=args_repr,
                    kwargs=kwargs_repr,
                    result=repr(_redact(result)),
                )
                return result
            except Exception as exc:
                log_event(
                    f.__name__,
                    user_id=user_id,
                    outcome="failure",
                    severity="error",
                    args=args_repr,
                    kwargs=kwargs_repr,
                    error=repr(_redact(str(exc))),
                    stacktrace=traceback.format_exc(),
                )
                raise

        @wraps(f)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            audit = kwargs.pop("audit", enabled)
            if not audit:
                return f(*args, **kwargs)

            user = kwargs.get("current_user") or kwargs.get("user") or kwargs.get("x_user")
            if user is None and (request := kwargs.get("request")) is not None:
                try:
                    user = request.headers.get("x-user") or request.headers.get("X-User")
                except Exception:  # pragma: no cover - defensive
                    user = None
            user_id = getattr(user, "username", None) or getattr(user, "id", None)
            if user_id is None and user is not None:
                user_id = str(user)

            args_repr = [repr(_redact(a)) for a in args]
            kwargs_repr = {k: repr(_redact(v, k)) for k, v in kwargs.items()}
            try:
                result = f(*args, **kwargs)
                log_event(
                    f.__name__,
                    user_id=user_id,
                    outcome="success",
                    severity="info",
                    args=args_repr,
                    kwargs=kwargs_repr,
                    result=repr(_redact(result)),
                )
                return result
            except Exception as exc:
                log_event(
                    f.__name__,
                    user_id=user_id,
                    outcome="failure",
                    severity="error",
                    args=args_repr,
                    kwargs=kwargs_repr,
                    error=repr(_redact(str(exc))),
                    stacktrace=traceback.format_exc(),
                )
                raise

        annotations = get_type_hints(f)
        async_wrapper.__annotations__ = annotations
        sync_wrapper.__annotations__ = annotations
        async_wrapper.__globals__.update(f.__globals__)  # type: ignore[attr-defined]
        sync_wrapper.__globals__.update(f.__globals__)  # type: ignore[attr-defined]
        return cast(F, async_wrapper if is_coro else sync_wrapper)

    if func is None:
        return cast(F, decorator)
    return decorator(func)

# SPDX-License-Identifier: MIT
"""Query, export, and maintenance functions for the audit log."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy import delete, func, select

from .. import rbac
from ..models import AuditLog, LogEntry
from ._db import LOG_RETENTION_DAYS, _get_db, alerts, logs
from ._dispatch import log_event


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


def query_logs(  # noqa: C901
    action: str | None = None,
    user_id: str | None = None,
    log_id: str | None = None,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    entity_id: str | None = None,
    entity_type: str | None = None,
    severity: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> List[LogEntry]:
    """Return logs filtered by optional fields and sorted by timestamp."""

    db = _get_db()
    stmt = select(AuditLog)
    if action is not None:
        stmt = stmt.where(AuditLog.action == action)
    if user_id is not None:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if log_id is not None:
        stmt = stmt.where(AuditLog.id == log_id)
    if entity_id is not None:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if entity_type is not None:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if severity is not None:
        stmt = stmt.where(AuditLog.severity == severity)
    if start is not None:
        stmt = stmt.where(AuditLog.timestamp >= start)
    if end is not None:
        stmt = stmt.where(AuditLog.timestamp <= end)
    stmt = stmt.order_by(AuditLog.timestamp)
    if limit is not None:
        stmt = stmt.limit(limit)
    if offset is not None:
        stmt = stmt.offset(offset)
    with db.session() as conn:
        rows = conn.execute(stmt).all()
    return [
        LogEntry(
            id=row.id,
            timestamp=row.timestamp,
            user_id=row.user_id,
            action=row.action,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            details=_coerce_details(row.details),
            severity=row.severity,
            ip_address=row.ip_address,
            prev_hash=row.prev_hash,
            hash=row.hash,
            document_hash=row.document_hash,
            provider_response=_coerce_details(row.provider_response),
        )
        for row in rows
    ]


def count_logs() -> int:
    """Return the total number of stored log entries."""

    db = _get_db()
    stmt = select(func.count()).select_from(AuditLog)
    with db.session() as conn:
        return int(conn.execute(stmt).scalar_one())


def export_logs(user_id: str, *, log_access: bool = True) -> List[LogEntry]:
    """Return all logs for export purposes with access control."""

    if user_id != "system" and not rbac.has_permission(user_id, "view_audit_log"):
        if log_access:
            log_event("audit_log_export", user_id=user_id, status="denied")
        raise PermissionError("Not authorized to export logs")
    entries = query_logs()
    if log_access:
        log_event("audit_log_export", user_id=user_id, status="success", count=len(entries))
    return entries


def purge_expired_logs(retention_days: int = LOG_RETENTION_DAYS) -> int:
    """Remove log entries older than ``retention_days``."""

    if retention_days <= 0:
        raise ValueError("retention_days must be positive")
    threshold = datetime.now(timezone.utc) - timedelta(days=retention_days)
    db = _get_db()
    with db.session() as conn:
        conn = conn.execution_options(allow_audit_log_mutations=True)
        result = conn.execute(delete(AuditLog).where(AuditLog.timestamp < threshold))
        count = result.rowcount or 0
    if count:
        log_event("logs_retention_purge", count=count)
    return count


def purge_logs(user_id: str, *, reason: str | None = None) -> int:
    """Admin-only removal of all log entries with explicit audit trail."""

    if not rbac.has_role(user_id, "admin"):
        raise PermissionError("Only admins may purge logs")
    db = _get_db()
    with db.session() as conn:
        conn = conn.execution_options(allow_audit_log_mutations=True)
        result = conn.execute(delete(AuditLog))
        count = result.rowcount or 0
    log_event("logs_purged", user_id=user_id, count=count, reason=reason)
    return count


def delete_log(log_id: str, user_id: str, *, reason: str | None = None) -> bool:
    """Admin-only removal of a single log entry with audit trail."""

    if not rbac.has_role(user_id, "admin"):
        raise PermissionError("Only admins may delete log entries")
    db = _get_db()
    with db.session() as conn:
        conn = conn.execution_options(allow_audit_log_mutations=True)
        result = conn.execute(delete(AuditLog).where(AuditLog.id == log_id))
        count = result.rowcount or 0
    log_event("log_deleted", user_id=user_id, log_id=log_id, count=count, reason=reason)
    return bool(count)


def clear_logs() -> None:
    """Remove all stored logs and alert hooks."""

    logs.clear()
    alerts.clear()

# SPDX-License-Identifier: MIT
"""Global state, constants, and database infrastructure for the audit log."""

from __future__ import annotations

import contextvars
import logging
import os
import re
from typing import Any, Callable, Dict, List, Literal, cast

from sqlalchemy import delete, event

from .. import log_connectors, rbac  # noqa: F401 — re-exported to _dispatch / _query
from ..database import Database, default_url
from ..models import Approval, AuditLog, LogEntry

# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

LOG_RETENTION_DAYS = 365

SENSITIVE_KEYS = {
    "access_token",
    "api_key",
    "authorization",
    "cookie",
    "csrf",
    "key",
    "password",
    "secret",
    "session",
    "token",
}

ERROR_TAXONOMY = frozenset(
    {
        "auth_error",
        "compliance_error",
        "configuration_error",
        "data_integrity_error",
        "dependency_error",
        "permission_error",
        "rate_limit_error",
        "system_error",
        "validation_error",
    }
)

# ---------------------------------------------------------------------------
# Private constants
# ---------------------------------------------------------------------------

_logger = logging.getLogger("docreview360.audit")
_JSON_TRUE_VALUES = {"1", "true", "yes", "on"}
_PRODUCTION_ENVS = {"prod", "production", "staging"}
_SEVERITY_ALIASES = {"warn": "warning", "err": "error", "fatal": "error"}
_VALID_SEVERITIES = {"info", "warning", "error"}
_ERROR_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,63}$")

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------

TRACE_ID: contextvars.ContextVar[str | None] = contextvars.ContextVar("trace_id", default=None)


class _LogList(list[LogEntry]):
    """In-memory mirror of log entries that also clears the database."""

    def clear(self) -> None:  # pragma: no cover - thin wrapper
        super().clear()
        try:
            db = _get_db()
        except Exception:
            return
        try:
            with db.session() as conn:
                conn.execute(delete(AuditLog).execution_options(allow_audit_log_mutations=True))
        except Exception:
            try:
                with db._engine.begin() as raw:
                    raw.exec_driver_sql("DROP TABLE IF EXISTS audit_logs")
                AuditLog.__table__.create(db._engine)
            except Exception:
                pass


logs: _LogList = _LogList()
alerts: List[tuple[str, Callable[[LogEntry], None]]] = []
_listeners: List[Callable[[LogEntry], None]] = []

_db: Database | None = None

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def _redact(value: Any, key: str | None = None) -> Any:
    if key and any(s in key.lower() for s in SENSITIVE_KEYS):
        if isinstance(value, str) and "[REDACTED]" in value:
            return value
        return "[REDACTED]"
    if isinstance(value, dict):
        return {k: _redact(v, k) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return type(value)(_redact(v) for v in value)
    return value


def _normalize_severity(value: str) -> Literal["info", "warning", "error"]:
    normalized = (value or "info").strip().lower()
    normalized = _SEVERITY_ALIASES.get(normalized, normalized)
    if normalized not in _VALID_SEVERITIES:
        normalized = "info"
    return cast(Literal["info", "warning", "error"], normalized)


def _normalize_error_code(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    if not text:
        return None
    if _ERROR_CODE_PATTERN.fullmatch(text) is None:
        return "system_error"
    if text not in ERROR_TAXONOMY:
        return "system_error"
    return text


def _should_emit_structured_runtime_logs() -> bool:
    log_format = os.getenv("DOCREVIEW360_LOG_FORMAT", "").strip().lower()
    if log_format == "json":
        return True
    env = os.getenv("DOCREVIEW360_ENV", "").strip().lower()
    if env in _PRODUCTION_ENVS:
        return True
    explicit = os.getenv("DOCREVIEW360_STRUCTURED_LOGS", "").strip().lower()
    return explicit in _JSON_TRUE_VALUES


def _emit_structured_runtime_log(entry: LogEntry) -> None:
    if not _should_emit_structured_runtime_logs():
        return

    import json

    payload = {
        "id": entry.id,
        "timestamp": entry.timestamp.isoformat(),
        "action": entry.action,
        "severity": entry.severity,
        "user_id": entry.user_id,
        "entity_type": entry.entity_type,
        "entity_id": entry.entity_id,
        "ip_address": entry.ip_address,
        "details": entry.details,
    }
    level = {
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
    }.get(entry.severity, logging.INFO)
    _logger.log(level, json.dumps(payload, sort_keys=True, default=str))


# ---------------------------------------------------------------------------
# Database infrastructure
# ---------------------------------------------------------------------------


def _get_db() -> Database:
    """Return a lazily initialized :class:`Database` instance."""

    global _db
    if _db is None:
        url = os.getenv("DOCREVIEW360_DATABASE_URL", default_url("sqlite"))
        _db = Database(url)
        _db.migrate()
        _install_worm_guard(_db)
    return _db


def _install_worm_guard(db: Database) -> None:
    """Prevent direct updates or deletes on the audit log table."""

    from sqlalchemy.sql.dml import Delete, Update

    engine = db._engine

    @event.listens_for(engine, "before_execute", retval=True)
    def _worm_guard(
        conn: Any,
        clauseelement: Any,
        multiparams: Any,
        params: Any,
        execution_options: Dict[str, Any],
    ) -> tuple[Any, Any, Any]:
        target_table = getattr(clauseelement, "table", None)
        if isinstance(clauseelement, (Delete, Update)) and target_table in {
            AuditLog.__table__,
            Approval.__table__,
        }:
            if not execution_options.get("allow_audit_log_mutations"):
                if target_table is AuditLog.__table__:
                    raise PermissionError("Audit log entries are immutable")
                raise PermissionError("Approvals are immutable")
        return clauseelement, multiparams, params

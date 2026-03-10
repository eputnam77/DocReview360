# SPDX-License-Identifier: MIT
"""Audit log package — public re-exports.

All names that were previously importable from ``docreview360.logs`` remain
available here, preserving backward compatibility for any code that imports
from the old flat module.
"""

from __future__ import annotations

from ..models import LogEntry
from ._db import LOG_RETENTION_DAYS, SENSITIVE_KEYS, ERROR_TAXONOMY, TRACE_ID, logs, alerts, _listeners, _get_db
from ._dispatch import (
    log_event,
    log_verification_failure,
    register_alert,
    register_listener,
    unregister_listener,
    log_stream,
    watch_logs,
    log_call,
    schedule_log_purge,
)
from ._query import (
    query_logs,
    count_logs,
    export_logs,
    purge_logs,
    purge_expired_logs,
    delete_log,
    clear_logs,
    verify_audit_log_chain,
)

__all__ = [
    "LogEntry",
    "log_event",
    "log_verification_failure",
    "query_logs",
    "count_logs",
    "export_logs",
    "purge_logs",
    "purge_expired_logs",
    "delete_log",
    "clear_logs",
    "verify_audit_log_chain",
    "log_stream",
    "register_alert",
    "register_listener",
    "unregister_listener",
    "watch_logs",
    "log_call",
    "schedule_log_purge",
    "TRACE_ID",
    "LOG_RETENTION_DAYS",
    "SENSITIVE_KEYS",
    "ERROR_TAXONOMY",
    "logs",
    "alerts",
]

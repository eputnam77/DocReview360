# SPDX-License-Identifier: MIT
"""Data retention policy enforcement for DocReview360.

Retention periods are configured via environment variables:

- ``DOCREVIEW360_RETAIN_AUDIT_LOGS_DAYS``   — audit log rows older than N days (0 = keep forever)
- ``DOCREVIEW360_RETAIN_SESSIONS_DAYS``     — expired user sessions older than N days (default 90)
- ``DOCREVIEW360_RETAIN_OIDC_STATES_DAYS``  — expired OIDC state records (default 1)
- ``DOCREVIEW360_RETAIN_WEBHOOKS_DAYS``     — webhook subscription records (default 365)

Call ``run_retention_pass()`` from a Celery beat task, the CLI, or a health
cron to purge expired rows.  Audit log deletion bypasses the WORM guard by
using ``execution_options(allow_audit_log_mutations=True)``; this is the only
path that should ever delete audit rows.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

log = logging.getLogger(__name__)


@dataclass
class RetentionPolicy:
    """Per-table retention configuration loaded from environment variables."""

    audit_logs_days: int = field(
        default_factory=lambda: int(
            os.environ.get("DOCREVIEW360_RETAIN_AUDIT_LOGS_DAYS", "0")
        )
    )
    sessions_days: int = field(
        default_factory=lambda: int(
            os.environ.get("DOCREVIEW360_RETAIN_SESSIONS_DAYS", "90")
        )
    )
    oidc_states_days: int = field(
        default_factory=lambda: int(
            os.environ.get("DOCREVIEW360_RETAIN_OIDC_STATES_DAYS", "1")
        )
    )
    webhook_records_days: int = field(
        default_factory=lambda: int(
            os.environ.get("DOCREVIEW360_RETAIN_WEBHOOKS_DAYS", "365")
        )
    )


@dataclass
class RetentionResult:
    """Summary of a completed retention pass."""

    deleted: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return sum(self.deleted.values())


def _cutoff(days: int) -> str:
    """Return an ISO-8601 cutoff timestamp ``days`` days in the past."""
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def run_retention_pass(policy: RetentionPolicy | None = None) -> RetentionResult:
    """Delete rows that exceed their configured retention period.

    Returns a :class:`RetentionResult` summarising rows removed per table.
    Audit logs with ``audit_logs_days=0`` are never deleted (keep-forever default).
    """
    from sqlalchemy import text

    from .logs._db import _get_db

    if policy is None:
        policy = RetentionPolicy()

    result = RetentionResult()
    db = _get_db()

    with db.session() as conn:
        # Expired user sessions older than the policy window.
        if policy.sessions_days > 0:
            r = conn.execute(
                text("DELETE FROM user_sessions WHERE expires_at < :cutoff"),
                {"cutoff": _cutoff(policy.sessions_days)},
            )
            result.deleted["user_sessions"] = r.rowcount

        # OIDC state records are always short-lived.
        if policy.oidc_states_days > 0:
            r = conn.execute(
                text("DELETE FROM oidc_states WHERE expires_at < :cutoff"),
                {"cutoff": _cutoff(policy.oidc_states_days)},
            )
            result.deleted["oidc_states"] = r.rowcount

        # Audit logs: only purge when explicitly configured (non-zero days).
        if policy.audit_logs_days > 0:
            r = conn.execution_options(allow_audit_log_mutations=True).execute(
                text("DELETE FROM audit_logs WHERE timestamp < :cutoff"),
                {"cutoff": _cutoff(policy.audit_logs_days)},
            )
            result.deleted["audit_logs"] = r.rowcount

    log.info("retention pass complete: %s", result.deleted)
    return result


def get_policy() -> RetentionPolicy:
    """Return the current retention policy derived from environment variables."""
    return RetentionPolicy()

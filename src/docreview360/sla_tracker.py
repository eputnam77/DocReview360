# SPDX-License-Identifier: MIT
"""SLA / deadline tracking for reviewer assignments (Item 44 Phase 8)."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any, Optional

from pydantic import BaseModel, Field
from sqlalchemy import text as _text

from .db_store import get_db

_logger = logging.getLogger(__name__)

# How many hours before due to show "due_soon"
_DUE_SOON_DAYS = 2

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class SLAConfig(BaseModel):
    """Default review SLA configuration per document type (and optional phase)."""

    doc_type: str
    phase: Optional[str] = None
    default_review_days: int = 14
    # Days before due to send reminders, e.g. [3, 1] → 3 days before, 1 day before
    reminder_days_before: list[int] = Field(default_factory=lambda: [3, 1])
    # Days overdue before escalating to SME
    escalation_threshold_days: int = 3


class DeadlineStatus(BaseModel):
    """Per-assignment deadline status."""

    assignment_id: str
    reviewer: str
    due_date: Optional[str]          # ISO date string or None
    days_remaining: Optional[int]    # negative means overdue
    status: str                      # on_track | due_soon | overdue | no_deadline
    overdue_days: int = 0            # 0 unless overdue


class SLASummary(BaseModel):
    """Project-level SLA rollup."""

    project_id: str
    total: int
    on_track: int
    due_soon: int
    overdue: int
    no_deadline: int
    max_overdue_days: int            # 0 if no overdue assignments


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def _ensure_table() -> None:
    db = get_db()
    with db.session() as conn:
        conn.execute(_text("""
            CREATE TABLE IF NOT EXISTS sla_configs (
                doc_type TEXT NOT NULL,
                phase TEXT,
                default_review_days INTEGER NOT NULL DEFAULT 14,
                reminder_days_before TEXT NOT NULL DEFAULT '3,1',
                escalation_threshold_days INTEGER NOT NULL DEFAULT 3,
                PRIMARY KEY (doc_type, phase)
            )
        """))


def _row_to_config(row: Any) -> SLAConfig:
    raw_days = row[3] or "3,1"
    try:
        reminder = [int(x) for x in raw_days.split(",") if x.strip()]
    except ValueError:
        reminder = [3, 1]
    return SLAConfig(
        doc_type=row[0],
        phase=row[1],
        default_review_days=int(row[2]),
        reminder_days_before=reminder,
        escalation_threshold_days=int(row[4]),
    )


# ---------------------------------------------------------------------------
# SLA config CRUD
# ---------------------------------------------------------------------------


def get_sla_config(doc_type: str, phase: Optional[str] = None) -> SLAConfig:
    """Return SLA config for a doc_type + phase (falls back to doc_type default)."""
    _ensure_table()
    db = get_db()
    with db.session() as conn:
        # Try phase-specific first, then doc_type default
        for p in (phase, None):
            row = conn.execute(
                _text(
                    "SELECT doc_type, phase, default_review_days, "
                    "reminder_days_before, escalation_threshold_days "
                    "FROM sla_configs WHERE doc_type = :dt AND phase IS :ph"
                ),
                {"dt": doc_type, "ph": p},
            ).fetchone()
            if row:
                return _row_to_config(row)
    return SLAConfig(doc_type=doc_type, phase=phase)


def list_sla_configs() -> list[SLAConfig]:
    """Return all stored SLA configs."""
    _ensure_table()
    db = get_db()
    with db.session() as conn:
        rows = conn.execute(
            _text(
                "SELECT doc_type, phase, default_review_days, "
                "reminder_days_before, escalation_threshold_days "
                "FROM sla_configs ORDER BY doc_type, phase"
            )
        ).fetchall()
    return [_row_to_config(r) for r in rows]


def set_sla_config(
    doc_type: str,
    *,
    phase: Optional[str] = None,
    default_review_days: int = 14,
    reminder_days_before: Optional[list[int]] = None,
    escalation_threshold_days: int = 3,
) -> SLAConfig:
    """Upsert an SLA config.

    Uses explicit SELECT + UPDATE/INSERT instead of ON CONFLICT UPSERT because
    SQLite's UPSERT conflict detection treats NULL != NULL in composite PKs,
    meaning rows with phase=NULL would never trigger the ON CONFLICT clause.
    """
    _ensure_table()
    reminder_str = ",".join(str(d) for d in (reminder_days_before or [3, 1]))
    db = get_db()
    with db.session() as conn:
        existing = conn.execute(
            _text(
                "SELECT 1 FROM sla_configs "
                "WHERE doc_type = :dt AND phase IS :ph"
            ),
            {"dt": doc_type, "ph": phase},
        ).fetchone()
        if existing:
            conn.execute(
                _text(
                    "UPDATE sla_configs SET "
                    "default_review_days = :days, "
                    "reminder_days_before = :reminder, "
                    "escalation_threshold_days = :esc "
                    "WHERE doc_type = :dt AND phase IS :ph"
                ),
                {
                    "dt": doc_type,
                    "ph": phase,
                    "days": default_review_days,
                    "reminder": reminder_str,
                    "esc": escalation_threshold_days,
                },
            )
        else:
            conn.execute(
                _text(
                    "INSERT INTO sla_configs "
                    "(doc_type, phase, default_review_days, reminder_days_before, escalation_threshold_days) "
                    "VALUES (:dt, :ph, :days, :reminder, :esc)"
                ),
                {
                    "dt": doc_type,
                    "ph": phase,
                    "days": default_review_days,
                    "reminder": reminder_str,
                    "esc": escalation_threshold_days,
                },
            )
    return get_sla_config(doc_type, phase)


# ---------------------------------------------------------------------------
# Deadline status computation
# ---------------------------------------------------------------------------


def get_days_remaining(assignment: Any) -> Optional[int]:
    """Return days until due (negative = overdue). None if no due_date."""
    raw = getattr(assignment, "due_date", None)
    if not raw:
        return None
    try:
        due = date.fromisoformat(str(raw)[:10])
        today = datetime.now(UTC).date()
        return (due - today).days
    except (ValueError, TypeError):
        return None


def get_deadline_status(assignment: Any) -> DeadlineStatus:
    """Classify an assignment's deadline status."""
    terminal = {"concurred", "signed", "declined", "replaced", "non_concurred"}
    status_val = getattr(assignment, "status", "")

    if status_val in terminal:
        return DeadlineStatus(
            assignment_id=assignment.id,
            reviewer=assignment.reviewer,
            due_date=getattr(assignment, "due_date", None),
            days_remaining=None,
            status="complete",
        )

    days = get_days_remaining(assignment)
    if days is None:
        return DeadlineStatus(
            assignment_id=assignment.id,
            reviewer=assignment.reviewer,
            due_date=None,
            days_remaining=None,
            status="no_deadline",
        )

    if days < 0:
        return DeadlineStatus(
            assignment_id=assignment.id,
            reviewer=assignment.reviewer,
            due_date=getattr(assignment, "due_date", None),
            days_remaining=days,
            status="overdue",
            overdue_days=-days,
        )
    if days <= _DUE_SOON_DAYS:
        return DeadlineStatus(
            assignment_id=assignment.id,
            reviewer=assignment.reviewer,
            due_date=getattr(assignment, "due_date", None),
            days_remaining=days,
            status="due_soon",
        )
    return DeadlineStatus(
        assignment_id=assignment.id,
        reviewer=assignment.reviewer,
        due_date=getattr(assignment, "due_date", None),
        days_remaining=days,
        status="on_track",
    )


# ---------------------------------------------------------------------------
# Project-level SLA summary
# ---------------------------------------------------------------------------


def get_sla_summary(project_id: str) -> SLASummary:
    """Return aggregate SLA status across all active assignments for a project."""
    try:
        from .review_assignments import list_assignments
        assignments = list_assignments(project_id)
    except Exception:
        assignments = []

    active = [a for a in assignments if a.status not in {"replaced"}]

    counts: dict[str, int] = {
        "on_track": 0, "due_soon": 0, "overdue": 0, "no_deadline": 0, "complete": 0
    }
    max_overdue = 0

    for a in active:
        ds = get_deadline_status(a)
        counts[ds.status] = counts.get(ds.status, 0) + 1
        if ds.overdue_days > max_overdue:
            max_overdue = ds.overdue_days

    return SLASummary(
        project_id=project_id,
        total=len(active),
        on_track=counts["on_track"],
        due_soon=counts["due_soon"],
        overdue=counts["overdue"],
        no_deadline=counts["no_deadline"],
        max_overdue_days=max_overdue,
    )


# ---------------------------------------------------------------------------
# Automated reminders
# ---------------------------------------------------------------------------


def run_sla_reminders(project_id: str, *, project_name: str = "") -> int:
    """Send reminder and escalation notifications for overdue/due-soon assignments.

    Returns number of notifications sent.
    """
    try:
        from .review_assignments import list_assignments
        from .notifications import send_notification
    except Exception as exc:
        _logger.debug("sla_reminders: import failed: %s", exc)
        return 0

    assignments = list_assignments(project_id)
    active = [
        a for a in assignments
        if a.status not in {"replaced", "concurred", "signed", "declined", "non_concurred"}
    ]

    sent = 0
    pname = project_name or project_id

    for a in active:
        ds = get_deadline_status(a)
        if ds.status == "overdue":
            msg = (
                f"OVERDUE: Reviewer '{a.reviewer}' is {ds.overdue_days} day(s) overdue "
                f"on project '{pname}'. /projects/{project_id}#reviewers"
            )
            try:
                send_notification(
                    "review.overdue",
                    message=msg,
                    project_id=project_id,
                    reviewer=a.reviewer,
                )
                sent += 1
            except Exception:
                pass

            # Escalate to SME if over threshold — best-effort
            try:
                from .notification_log import log_notification
                log_notification(
                    "review.overdue",
                    msg,
                    project_id=project_id,
                    reviewer=a.reviewer,
                )
            except Exception:
                pass

        elif ds.status == "due_soon":
            msg = (
                f"Reminder: Reviewer '{a.reviewer}' has {ds.days_remaining} day(s) "
                f"remaining to complete review of project '{pname}'. "
                f"/projects/{project_id}#reviewers"
            )
            try:
                send_notification(
                    "review.reminder",
                    message=msg,
                    project_id=project_id,
                    reviewer=a.reviewer,
                )
                sent += 1
            except Exception:
                pass

    return sent


# ---------------------------------------------------------------------------
# Celery beat registration
# ---------------------------------------------------------------------------


def register_sla_beat_task(interval_minutes: int = 60) -> None:
    """Register a Celery beat task to run SLA reminders on a schedule."""
    try:
        from .celery_app import app as celery_app

        @celery_app.task(name="docreview360.sla_reminder_sweep")
        def _sla_reminder_sweep() -> None:
            """Sweep all projects and send SLA reminders."""
            try:
                from .search import list_projects
                projects = list_projects()
                for p in projects:
                    run_sla_reminders(p.id, project_name=p.name)
            except Exception as exc:  # pragma: no cover
                _logger.warning("SLA reminder sweep failed: %s", exc)

        celery_app.conf.beat_schedule = getattr(celery_app.conf, "beat_schedule", {}) or {}
        celery_app.conf.beat_schedule["sla_reminder_sweep"] = {
            "task": "docreview360.sla_reminder_sweep",
            "schedule": timedelta(minutes=interval_minutes),
        }
        _logger.info("SLA reminder beat task registered (every %d min)", interval_minutes)
    except Exception as exc:  # pragma: no cover
        _logger.debug("SLA beat registration skipped: %s", exc)

# SPDX-License-Identifier: MIT
"""Review assignment lifecycle — SQLite-backed model and CRUD (Item 44)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field
from sqlalchemy import text as _text

from .db_store import get_db

# ---------------------------------------------------------------------------
# Valid status values
# ---------------------------------------------------------------------------

REVIEW_ASSIGNMENT_STATUSES = (
    "invited",
    "reviewing",
    "feedback_submitted",
    "concurred",
    "non_concurred",
    "signed",
    "declined",
    "replaced",
)
TERMINAL_STATUSES = frozenset({"concurred", "non_concurred", "signed", "declined", "replaced"})


# ---------------------------------------------------------------------------
# Pydantic model (API layer)
# ---------------------------------------------------------------------------


class ReviewAssignmentModel(BaseModel):
    """Reviewer assignment with full lifecycle tracking."""

    id: str
    project_id: str
    reviewer: str
    status: str = "invited"
    requested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    signed_at: Optional[datetime] = None
    signature_id: Optional[str] = None
    due_date: Optional[datetime] = None
    replaced_by: Optional[str] = None
    replacement_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

_COLUMNS = (
    "id", "project_id", "reviewer", "status",
    "requested_at", "started_at", "completed_at", "signed_at",
    "signature_id", "due_date", "replaced_by", "replacement_reason",
)


def _ensure_table() -> None:
    """Create review_assignments table if not present."""
    db = get_db()
    with db.session() as conn:
        conn.execute(_text("""
            CREATE TABLE IF NOT EXISTS review_assignments (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                reviewer TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'invited',
                requested_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                signed_at TEXT,
                signature_id TEXT,
                due_date TEXT,
                replaced_by TEXT,
                replacement_reason TEXT
            )
        """))
        conn.execute(_text(
            "CREATE INDEX IF NOT EXISTS ix_ra_project "
            "ON review_assignments(project_id)"
        ))
        conn.execute(_text(
            "CREATE INDEX IF NOT EXISTS ix_ra_reviewer "
            "ON review_assignments(reviewer)"
        ))


def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _row_to_model(row: Any) -> ReviewAssignmentModel:
    return ReviewAssignmentModel(
        id=row[0],
        project_id=row[1],
        reviewer=row[2],
        status=row[3],
        requested_at=_parse_dt(row[4]) or datetime.now(UTC),
        started_at=_parse_dt(row[5]),
        completed_at=_parse_dt(row[6]),
        signed_at=_parse_dt(row[7]),
        signature_id=row[8],
        due_date=_parse_dt(row[9]),
        replaced_by=row[10],
        replacement_reason=row[11],
    )


_SELECT_ALL = (
    "SELECT id, project_id, reviewer, status, "
    "requested_at, started_at, completed_at, signed_at, "
    "signature_id, due_date, replaced_by, replacement_reason "
    "FROM review_assignments"
)


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


def create_assignment(
    project_id: str,
    reviewer: str,
    *,
    due_date: Optional[datetime] = None,
    status: str = "invited",
) -> ReviewAssignmentModel:
    """Create a new review assignment and return it."""
    _ensure_table()
    now = datetime.now(UTC)
    assignment = ReviewAssignmentModel(
        id=str(uuid.uuid4()),
        project_id=project_id,
        reviewer=reviewer,
        status=status,
        requested_at=now,
        due_date=due_date,
    )
    db = get_db()
    with db.session() as conn:
        conn.execute(
            _text("""
                INSERT INTO review_assignments
                    (id, project_id, reviewer, status, requested_at,
                     started_at, completed_at, signed_at,
                     signature_id, due_date, replaced_by, replacement_reason)
                VALUES
                    (:id, :project_id, :reviewer, :status, :requested_at,
                     :started_at, :completed_at, :signed_at,
                     :signature_id, :due_date, :replaced_by, :replacement_reason)
            """),
            {
                "id": assignment.id,
                "project_id": assignment.project_id,
                "reviewer": assignment.reviewer,
                "status": assignment.status,
                "requested_at": assignment.requested_at.isoformat(),
                "started_at": None,
                "completed_at": None,
                "signed_at": None,
                "signature_id": None,
                "due_date": due_date.isoformat() if due_date else None,
                "replaced_by": None,
                "replacement_reason": None,
            },
        )
    return assignment


def list_assignments(project_id: str) -> list[ReviewAssignmentModel]:
    """Return all assignments for a project ordered by requested_at."""
    _ensure_table()
    db = get_db()
    with db.session() as conn:
        rows = conn.execute(
            _text(f"{_SELECT_ALL} WHERE project_id = :project_id ORDER BY requested_at"),
            {"project_id": project_id},
        ).fetchall()
    return [_row_to_model(row) for row in rows]


def list_all_assignments_for_reviewer(reviewer: str) -> list[ReviewAssignmentModel]:
    """Return all assignments across all projects for a specific reviewer."""
    _ensure_table()
    db = get_db()
    with db.session() as conn:
        rows = conn.execute(
            _text(f"{_SELECT_ALL} WHERE reviewer = :reviewer ORDER BY requested_at"),
            {"reviewer": reviewer},
        ).fetchall()
    return [_row_to_model(row) for row in rows]


def get_assignment(assignment_id: str) -> Optional[ReviewAssignmentModel]:
    """Return a single assignment by ID, or None if not found."""
    _ensure_table()
    db = get_db()
    with db.session() as conn:
        row = conn.execute(
            _text(f"{_SELECT_ALL} WHERE id = :id"),
            {"id": assignment_id},
        ).fetchone()
    return _row_to_model(row) if row else None


def _update_fields(assignment_id: str, **kwargs: Any) -> ReviewAssignmentModel:
    """Apply arbitrary field updates to an assignment row."""
    _ensure_table()
    set_clause = ", ".join(f"{k} = :{k}" for k in kwargs)
    db = get_db()
    with db.session() as conn:
        conn.execute(
            _text(f"UPDATE review_assignments SET {set_clause} WHERE id = :assignment_id"),
            {"assignment_id": assignment_id, **kwargs},
        )
    result = get_assignment(assignment_id)
    if result is None:
        raise KeyError(f"Assignment {assignment_id!r} not found")
    return result


def transition_status(
    assignment_id: str,
    new_status: str,
    *,
    ts_field: Optional[str] = None,
) -> ReviewAssignmentModel:
    """Transition an assignment to *new_status*, optionally stamping a timestamp field."""
    now = datetime.now(UTC).isoformat()
    kwargs: dict[str, Any] = {"status": new_status}
    if ts_field:
        kwargs[ts_field] = now
    return _update_fields(assignment_id, **kwargs)


def replace_assignment(
    assignment_id: str,
    replacement_reviewer: str,
    reason: str,
    *,
    due_date: Optional[datetime] = None,
) -> tuple[ReviewAssignmentModel, ReviewAssignmentModel]:
    """Replace an assignment and create a new one for the replacement reviewer."""
    original = get_assignment(assignment_id)
    if original is None:
        raise KeyError(f"Assignment {assignment_id!r} not found")
    new_assignment = create_assignment(
        original.project_id, replacement_reviewer, due_date=due_date
    )
    _update_fields(
        assignment_id,
        status="replaced",
        replaced_by=new_assignment.id,
        replacement_reason=reason,
    )
    updated_original = get_assignment(assignment_id)
    assert updated_original is not None  # noqa: S101 — guaranteed by _update_fields
    return updated_original, new_assignment


def delete_assignment(assignment_id: str) -> None:
    """Permanently remove an assignment record."""
    _ensure_table()
    db = get_db()
    with db.session() as conn:
        conn.execute(
            _text("DELETE FROM review_assignments WHERE id = :id"),
            {"id": assignment_id},
        )


def migrate_reviewers_to_assignments(
    project_id: str, reviewers: list[str]
) -> list[ReviewAssignmentModel]:
    """One-time migration: convert bare reviewer usernames to ReviewAssignment records.

    Creates assignments in ``"reviewing"`` status (the first active state) so that
    existing project state is preserved.  Skips reviewers already assigned.
    """
    existing = {a.reviewer for a in list_assignments(project_id)}
    created = []
    for reviewer in reviewers:
        if reviewer not in existing:
            created.append(create_assignment(project_id, reviewer, status="reviewing"))
    return created

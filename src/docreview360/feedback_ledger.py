# SPDX-License-Identifier: MIT
"""Feedback ledger — structured reviewer feedback with threaded conversation (Item 44 Phase 3)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field
from sqlalchemy import text as _text

from .db_store import get_db

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FEEDBACK_STATUSES = ("open", "accepted", "rejected", "resolved")
FEEDBACK_TYPES = ("comment", "question", "suggestion", "non_concurrence")
TERMINAL_FEEDBACK_STATUSES = frozenset({"accepted", "rejected", "resolved"})


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class FeedbackItem(BaseModel):
    """A structured feedback item from a reviewer on a project."""

    id: str
    project_id: str
    assignment_id: Optional[str] = None
    reviewer: str
    feedback_type: str = "comment"
    text: str
    phase: Optional[str] = None
    status: str = "open"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    disposition_by: Optional[str] = None
    disposition_at: Optional[datetime] = None
    disposition_reason: Optional[str] = None
    # FK to parent FeedbackItem id for threaded replies
    parent_id: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    # Reviewer can mark a "question" as satisfied after SME answers
    question_satisfied: bool = False


class FeedbackProgress(BaseModel):
    """Summary counts for the feedback ledger of a project."""

    total: int
    open: int
    accepted: int
    rejected: int
    resolved: int
    by_type: dict[str, int]
    addressed: int  # accepted + rejected + resolved


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

_SELECT_ALL = (
    "SELECT id, project_id, assignment_id, reviewer, feedback_type, text, phase, status, "
    "created_at, disposition_by, disposition_at, disposition_reason, parent_id, tags, "
    "question_satisfied "
    "FROM feedback_items"
)


def _ensure_table() -> None:
    """Create feedback_items table if not present."""
    db = get_db()
    with db.session() as conn:
        conn.execute(_text("""
            CREATE TABLE IF NOT EXISTS feedback_items (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                assignment_id TEXT,
                reviewer TEXT NOT NULL,
                feedback_type TEXT NOT NULL DEFAULT 'comment',
                text TEXT NOT NULL,
                phase TEXT,
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL,
                disposition_by TEXT,
                disposition_at TEXT,
                disposition_reason TEXT,
                parent_id TEXT,
                tags TEXT NOT NULL DEFAULT '',
                question_satisfied INTEGER NOT NULL DEFAULT 0
            )
        """))
        conn.execute(_text(
            "CREATE INDEX IF NOT EXISTS ix_fi_project "
            "ON feedback_items(project_id)"
        ))
        conn.execute(_text(
            "CREATE INDEX IF NOT EXISTS ix_fi_assignment "
            "ON feedback_items(assignment_id)"
        ))
        conn.execute(_text(
            "CREATE INDEX IF NOT EXISTS ix_fi_reviewer "
            "ON feedback_items(reviewer)"
        ))


def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _row_to_model(row: Any) -> FeedbackItem:
    tags_raw = row[13] or ""
    tags = [t for t in tags_raw.split(",") if t.strip()] if tags_raw else []
    return FeedbackItem(
        id=row[0],
        project_id=row[1],
        assignment_id=row[2],
        reviewer=row[3],
        feedback_type=row[4],
        text=row[5],
        phase=row[6],
        status=row[7],
        created_at=_parse_dt(row[8]) or datetime.now(UTC),
        disposition_by=row[9],
        disposition_at=_parse_dt(row[10]),
        disposition_reason=row[11],
        parent_id=row[12],
        tags=tags,
        question_satisfied=bool(row[14]),
    )


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


def create_feedback_item(
    project_id: str,
    reviewer: str,
    text: str,
    *,
    assignment_id: Optional[str] = None,
    feedback_type: str = "comment",
    phase: Optional[str] = None,
    parent_id: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> FeedbackItem:
    """Create and persist a new feedback item."""
    _ensure_table()
    now = datetime.now(UTC)
    item = FeedbackItem(
        id=str(uuid.uuid4()),
        project_id=project_id,
        assignment_id=assignment_id,
        reviewer=reviewer,
        feedback_type=feedback_type,
        text=text,
        phase=phase,
        status="open",
        created_at=now,
        parent_id=parent_id,
        tags=tags or [],
    )
    db = get_db()
    with db.session() as conn:
        conn.execute(
            _text("""
                INSERT INTO feedback_items
                    (id, project_id, assignment_id, reviewer, feedback_type, text, phase,
                     status, created_at, disposition_by, disposition_at, disposition_reason,
                     parent_id, tags, question_satisfied)
                VALUES
                    (:id, :project_id, :assignment_id, :reviewer, :feedback_type, :text, :phase,
                     :status, :created_at, :disposition_by, :disposition_at, :disposition_reason,
                     :parent_id, :tags, :question_satisfied)
            """),
            {
                "id": item.id,
                "project_id": item.project_id,
                "assignment_id": item.assignment_id,
                "reviewer": item.reviewer,
                "feedback_type": item.feedback_type,
                "text": item.text,
                "phase": item.phase,
                "status": item.status,
                "created_at": item.created_at.isoformat(),
                "disposition_by": None,
                "disposition_at": None,
                "disposition_reason": None,
                "parent_id": item.parent_id,
                "tags": ",".join(item.tags),
                "question_satisfied": 0,
            },
        )
    return item


def list_feedback_items(
    project_id: str,
    *,
    reviewer: Optional[str] = None,
    feedback_type: Optional[str] = None,
    status: Optional[str] = None,
    phase: Optional[str] = None,
    assignment_id: Optional[str] = None,
    parent_id: Optional[str] = None,
) -> list[FeedbackItem]:
    """Return feedback items for a project, with optional filters."""
    _ensure_table()
    conditions: list[str] = ["project_id = :project_id"]
    params: dict[str, Any] = {"project_id": project_id}

    if reviewer:
        conditions.append("reviewer = :reviewer")
        params["reviewer"] = reviewer
    if feedback_type:
        conditions.append("feedback_type = :feedback_type")
        params["feedback_type"] = feedback_type
    if status:
        conditions.append("status = :status")
        params["status"] = status
    if phase:
        conditions.append("phase = :phase")
        params["phase"] = phase
    if assignment_id:
        conditions.append("assignment_id = :assignment_id")
        params["assignment_id"] = assignment_id
    if parent_id is not None:
        conditions.append("parent_id = :parent_id")
        params["parent_id"] = parent_id

    where = " AND ".join(conditions)
    db = get_db()
    with db.session() as conn:
        rows = conn.execute(
            _text(f"{_SELECT_ALL} WHERE {where} ORDER BY created_at"),
            params,
        ).fetchall()
    return [_row_to_model(row) for row in rows]


def get_feedback_item(item_id: str) -> Optional[FeedbackItem]:
    """Return a single feedback item by id."""
    _ensure_table()
    db = get_db()
    with db.session() as conn:
        row = conn.execute(
            _text(f"{_SELECT_ALL} WHERE id = :id"),
            {"id": item_id},
        ).fetchone()
    return _row_to_model(row) if row else None


def _update_fields(item_id: str, **kwargs: Any) -> FeedbackItem:
    """Apply field updates to a feedback item row."""
    _ensure_table()
    set_clause = ", ".join(f"{k} = :{k}" for k in kwargs)
    db = get_db()
    with db.session() as conn:
        conn.execute(
            _text(f"UPDATE feedback_items SET {set_clause} WHERE id = :item_id"),
            {"item_id": item_id, **kwargs},
        )
    result = get_feedback_item(item_id)
    if result is None:
        raise KeyError(f"FeedbackItem {item_id!r} not found")
    return result


def dispose_feedback_item(
    item_id: str,
    new_status: str,
    *,
    disposition_by: str,
    disposition_reason: Optional[str] = None,
) -> FeedbackItem:
    """Set the disposition status on a feedback item (accept / reject / resolve)."""
    if new_status not in TERMINAL_FEEDBACK_STATUSES:
        raise ValueError(f"Invalid disposition status: {new_status!r}")
    now = datetime.now(UTC).isoformat()
    return _update_fields(
        item_id,
        status=new_status,
        disposition_by=disposition_by,
        disposition_at=now,
        disposition_reason=disposition_reason,
    )


def reply_to_feedback(
    parent_id: str,
    reviewer: str,
    text: str,
    *,
    assignment_id: Optional[str] = None,
) -> FeedbackItem:
    """Create a threaded reply to an existing feedback item."""
    parent = get_feedback_item(parent_id)
    if parent is None:
        raise KeyError(f"Parent feedback item {parent_id!r} not found")
    return create_feedback_item(
        parent.project_id,
        reviewer,
        text,
        assignment_id=assignment_id or parent.assignment_id,
        feedback_type=parent.feedback_type,
        phase=parent.phase,
        parent_id=parent_id,
    )


def mark_question_satisfied(item_id: str) -> FeedbackItem:
    """Reviewer marks a 'question' type item as satisfied."""
    return _update_fields(item_id, question_satisfied=1)


def get_feedback_progress(project_id: str, *, phase: Optional[str] = None) -> FeedbackProgress:
    """Return aggregate progress counts for a project's feedback ledger.

    Only top-level items (no parent) are counted — replies are not dispositioned
    independently.
    """
    _ensure_table()
    conditions = ["project_id = :project_id", "parent_id IS NULL"]
    params: dict[str, Any] = {"project_id": project_id}
    if phase:
        conditions.append("phase = :phase")
        params["phase"] = phase

    where = " AND ".join(conditions)
    db = get_db()
    with db.session() as conn:
        rows = conn.execute(
            _text(
                f"SELECT status, feedback_type FROM feedback_items WHERE {where}"
            ),
            params,
        ).fetchall()

    total = len(rows)
    counts: dict[str, int] = {"open": 0, "accepted": 0, "rejected": 0, "resolved": 0}
    by_type: dict[str, int] = {}
    for status, fb_type in rows:
        counts[status] = counts.get(status, 0) + 1
        by_type[fb_type] = by_type.get(fb_type, 0) + 1

    addressed = counts["accepted"] + counts["rejected"] + counts["resolved"]
    return FeedbackProgress(
        total=total,
        open=counts["open"],
        accepted=counts["accepted"],
        rejected=counts["rejected"],
        resolved=counts["resolved"],
        by_type=by_type,
        addressed=addressed,
    )

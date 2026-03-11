# SPDX-License-Identifier: MIT
"""Project lifecycle status — draft → in_review → … → closed (Item 44 Phase 7)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, Optional

from pydantic import BaseModel
from sqlalchemy import text as _text

from .db_store import get_db

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_LIFECYCLE_STATUSES = (
    "draft",
    "in_review",
    "reviewed",
    "ready_for_publication",
    "published",
    "submitted_to_records",
    "closed",
)

# Which transitions are permitted
VALID_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"in_review"},
    "in_review": {"reviewed", "draft"},
    "reviewed": {"ready_for_publication", "in_review"},
    "ready_for_publication": {"published", "reviewed"},
    "published": {"submitted_to_records"},
    "submitted_to_records": {"closed"},
    "closed": set(),
}

# Statuses that block new feedback submission
FEEDBACK_BLOCKED_STATUSES = frozenset(
    {"ready_for_publication", "published", "submitted_to_records", "closed"}
)

# Statuses that freeze document content
DOCUMENT_FROZEN_STATUSES = frozenset(
    {"ready_for_publication", "published", "submitted_to_records", "closed"}
)

TERMINAL_LIFECYCLE_STATUSES = frozenset({"submitted_to_records", "closed"})


# ---------------------------------------------------------------------------
# Pydantic model
# ---------------------------------------------------------------------------


class ProjectLifecycleRecord(BaseModel):
    """Persisted lifecycle state for a project."""

    project_id: str
    status: str = "draft"
    updated_at: datetime
    set_by: Optional[str] = None
    published_ref: Optional[str] = None      # External publication reference
    published_at: Optional[str] = None       # ISO date of publication
    published_venue: Optional[str] = None    # e.g. "Federal Register Vol 89"


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def _ensure_table() -> None:
    db = get_db()
    with db.session() as conn:
        conn.execute(_text("""
            CREATE TABLE IF NOT EXISTS project_lifecycle (
                project_id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'draft',
                updated_at TEXT NOT NULL,
                set_by TEXT,
                published_ref TEXT,
                published_at TEXT,
                published_venue TEXT
            )
        """))


def _row_to_record(row: Any) -> ProjectLifecycleRecord:
    return ProjectLifecycleRecord(
        project_id=row[0],
        status=row[1],
        updated_at=datetime.fromisoformat(row[2]),
        set_by=row[3],
        published_ref=row[4],
        published_at=row[5],
        published_venue=row[6],
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_lifecycle(project_id: str) -> ProjectLifecycleRecord:
    """Return the lifecycle record for a project, defaulting to 'draft'."""
    _ensure_table()
    db = get_db()
    with db.session() as conn:
        row = conn.execute(
            _text(
                "SELECT project_id, status, updated_at, set_by, "
                "published_ref, published_at, published_venue "
                "FROM project_lifecycle WHERE project_id = :pid"
            ),
            {"pid": project_id},
        ).fetchone()
    if row:
        return _row_to_record(row)
    return ProjectLifecycleRecord(
        project_id=project_id,
        status="draft",
        updated_at=datetime.now(UTC),
    )


def set_lifecycle(
    project_id: str,
    new_status: str,
    *,
    set_by: str = "",
) -> ProjectLifecycleRecord:
    """Transition a project to a new lifecycle status.

    Raises ValueError for invalid statuses or disallowed transitions.
    """
    if new_status not in PROJECT_LIFECYCLE_STATUSES:
        raise ValueError(
            f"Invalid lifecycle status {new_status!r}. "
            f"Valid statuses: {PROJECT_LIFECYCLE_STATUSES}"
        )
    _ensure_table()
    current = get_lifecycle(project_id)
    allowed = VALID_TRANSITIONS.get(current.status, set())
    if new_status not in allowed and new_status != current.status:
        raise ValueError(
            f"Cannot transition from '{current.status}' to '{new_status}'. "
            f"Allowed: {sorted(allowed) or 'none (terminal)'}"
        )
    now = datetime.now(UTC).isoformat()
    db = get_db()
    with db.session() as conn:
        conn.execute(
            _text("""
                INSERT INTO project_lifecycle
                    (project_id, status, updated_at, set_by, published_ref, published_at, published_venue)
                VALUES
                    (:pid, :status, :now, :set_by, :pub_ref, :pub_at, :pub_venue)
                ON CONFLICT(project_id) DO UPDATE SET
                    status = excluded.status,
                    updated_at = excluded.updated_at,
                    set_by = excluded.set_by
            """),
            {
                "pid": project_id,
                "status": new_status,
                "now": now,
                "set_by": set_by or None,
                "pub_ref": current.published_ref,
                "pub_at": current.published_at,
                "pub_venue": current.published_venue,
            },
        )
    return get_lifecycle(project_id)


def set_published_metadata(
    project_id: str,
    *,
    published_ref: Optional[str] = None,
    published_at: Optional[str] = None,
    published_venue: Optional[str] = None,
) -> ProjectLifecycleRecord:
    """Store external publication details (reference number, date, venue)."""
    _ensure_table()
    now = datetime.now(UTC).isoformat()
    db = get_db()
    with db.session() as conn:
        conn.execute(
            _text("""
                INSERT INTO project_lifecycle
                    (project_id, status, updated_at, set_by, published_ref, published_at, published_venue)
                VALUES
                    (:pid, 'published', :now, NULL, :pub_ref, :pub_at, :pub_venue)
                ON CONFLICT(project_id) DO UPDATE SET
                    published_ref = excluded.published_ref,
                    published_at = excluded.published_at,
                    published_venue = excluded.published_venue,
                    updated_at = excluded.updated_at
            """),
            {
                "pid": project_id,
                "now": now,
                "pub_ref": published_ref,
                "pub_at": published_at,
                "pub_venue": published_venue,
            },
        )
    return get_lifecycle(project_id)


def is_feedback_blocked(project_id: str) -> bool:
    """Return True if the project lifecycle status blocks new feedback."""
    lc = get_lifecycle(project_id)
    return lc.status in FEEDBACK_BLOCKED_STATUSES

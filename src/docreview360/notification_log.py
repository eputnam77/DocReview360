# SPDX-License-Identifier: MIT
"""Notification log — persisted record of sent notifications (Item 44 Phase 2)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field
from sqlalchemy import text as _text

from .db_store import get_db


class NotificationLogEntry(BaseModel):
    """A record of a single notification dispatch."""

    id: str
    event: str
    message: str
    project_id: Optional[str] = None
    reviewer: Optional[str] = None
    sent_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    channel: str = "unknown"  # email | slack | teams | webhook | unknown


_SELECT_ALL = (
    "SELECT id, event, message, project_id, reviewer, sent_at, channel "
    "FROM notification_log"
)


def _ensure_table() -> None:
    db = get_db()
    with db.session() as conn:
        conn.execute(_text("""
            CREATE TABLE IF NOT EXISTS notification_log (
                id TEXT PRIMARY KEY,
                event TEXT NOT NULL,
                message TEXT NOT NULL,
                project_id TEXT,
                reviewer TEXT,
                sent_at TEXT NOT NULL,
                channel TEXT NOT NULL DEFAULT 'unknown'
            )
        """))
        conn.execute(_text(
            "CREATE INDEX IF NOT EXISTS ix_nl_project ON notification_log(project_id)"
        ))


def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _row_to_entry(row: Any) -> NotificationLogEntry:
    return NotificationLogEntry(
        id=row[0],
        event=row[1],
        message=row[2],
        project_id=row[3],
        reviewer=row[4],
        sent_at=_parse_dt(row[5]) or datetime.now(UTC),
        channel=row[6],
    )


def log_notification(
    event: str,
    message: str,
    *,
    project_id: Optional[str] = None,
    reviewer: Optional[str] = None,
    channel: str = "unknown",
) -> NotificationLogEntry:
    """Persist a notification dispatch to the log."""
    _ensure_table()
    entry = NotificationLogEntry(
        id=str(uuid.uuid4()),
        event=event,
        message=message,
        project_id=project_id,
        reviewer=reviewer,
        sent_at=datetime.now(UTC),
        channel=channel,
    )
    db = get_db()
    with db.session() as conn:
        conn.execute(
            _text("""
                INSERT INTO notification_log
                    (id, event, message, project_id, reviewer, sent_at, channel)
                VALUES
                    (:id, :event, :message, :project_id, :reviewer, :sent_at, :channel)
            """),
            {
                "id": entry.id,
                "event": entry.event,
                "message": entry.message,
                "project_id": entry.project_id,
                "reviewer": entry.reviewer,
                "sent_at": entry.sent_at.isoformat(),
                "channel": entry.channel,
            },
        )
    return entry


def list_notification_log(
    project_id: str,
    *,
    limit: int = 50,
) -> list[NotificationLogEntry]:
    """Return recent notification log entries for a project."""
    _ensure_table()
    db = get_db()
    with db.session() as conn:
        rows = conn.execute(
            _text(
                f"{_SELECT_ALL} WHERE project_id = :project_id "
                "ORDER BY sent_at DESC LIMIT :limit"
            ),
            {"project_id": project_id, "limit": limit},
        ).fetchall()
    return [_row_to_entry(row) for row in rows]

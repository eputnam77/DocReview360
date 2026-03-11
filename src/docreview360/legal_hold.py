# SPDX-License-Identifier: MIT
"""Legal hold management for eDiscovery and compliance."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .models import LegalHold, LegalHoldDocument


def create_legal_hold(
    db: Session,
    name: str,
    reason: str | None,
    created_by: str,
    expires_at: datetime | None = None,
) -> LegalHold:
    """Create a new legal hold."""
    now = datetime.now(timezone.utc)
    hold = LegalHold(
        id=str(uuid.uuid4()),
        hold_name=name,
        hold_reason=reason,
        created_by=created_by,
        created_at=now,
        expires_at=expires_at,
        status="active",
    )
    db.add(hold)
    db.commit()
    db.refresh(hold)
    return hold


def get_legal_hold(db: Session, hold_id: str) -> LegalHold | None:
    """Fetch a legal hold by ID."""
    return db.query(LegalHold).filter(LegalHold.id == hold_id).first()


def list_legal_holds(db: Session, status: str | None = None) -> list[LegalHold]:
    """List legal holds, optionally filtered by status."""
    q = db.query(LegalHold)
    if status:
        q = q.filter(LegalHold.status == status)
    return q.order_by(LegalHold.created_at.desc()).all()


def add_document_to_hold(
    db: Session, hold_id: str, document_id: str, added_by: str
) -> LegalHoldDocument:
    """Add a document to a legal hold. Returns existing record if already added."""
    existing = (
        db.query(LegalHoldDocument)
        .filter(
            LegalHoldDocument.hold_id == hold_id,
            LegalHoldDocument.document_id == document_id,
        )
        .first()
    )
    if existing:
        return existing
    entry = LegalHoldDocument(
        id=str(uuid.uuid4()),
        hold_id=hold_id,
        document_id=document_id,
        added_at=datetime.now(timezone.utc),
        added_by=added_by,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def remove_document_from_hold(db: Session, hold_id: str, document_id: str) -> bool:
    """Remove a document from a legal hold. Returns True if removed."""
    entry = (
        db.query(LegalHoldDocument)
        .filter(
            LegalHoldDocument.hold_id == hold_id,
            LegalHoldDocument.document_id == document_id,
        )
        .first()
    )
    if entry is None:
        return False
    db.delete(entry)
    db.commit()
    return True


def release_hold(db: Session, hold_id: str, released_by: str) -> LegalHold:
    """Release a legal hold, preventing further additions."""
    hold = db.query(LegalHold).filter(LegalHold.id == hold_id).first()
    if hold is None:
        raise ValueError(f"Legal hold {hold_id!r} not found")
    hold.status = "released"
    hold.released_by = released_by
    hold.released_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(hold)
    return hold


def get_document_holds(db: Session, document_id: str) -> list[LegalHold]:
    """Return all active legal holds that include a specific document."""
    entries = (
        db.query(LegalHoldDocument)
        .filter(LegalHoldDocument.document_id == document_id)
        .all()
    )
    hold_ids = [e.hold_id for e in entries]
    if not hold_ids:
        return []
    return (
        db.query(LegalHold)
        .filter(LegalHold.id.in_(hold_ids), LegalHold.status == "active")
        .all()
    )


def is_document_on_hold(db: Session, document_id: str) -> bool:
    """Return True if the document is under at least one active legal hold."""
    return len(get_document_holds(db, document_id)) > 0

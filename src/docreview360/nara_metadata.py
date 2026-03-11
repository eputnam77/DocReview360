# SPDX-License-Identifier: MIT
"""NARA records management metadata helpers."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from .models import NaraMetadata


def get_nara_metadata(db: Session, document_id: str) -> NaraMetadata | None:
    """Return NARA metadata for a document, or None if not set."""
    return db.query(NaraMetadata).filter(NaraMetadata.document_id == document_id).first()


def set_nara_metadata(db: Session, document_id: str, **kwargs: Any) -> NaraMetadata:
    """Create or update NARA metadata for a document (upsert)."""
    record = db.query(NaraMetadata).filter(NaraMetadata.document_id == document_id).first()
    now = datetime.now(timezone.utc)
    if record is None:
        record = NaraMetadata(id=str(uuid.uuid4()), document_id=document_id, created_at=now)
        db.add(record)
    record.updated_at = now
    allowed = {
        "schedule_number",
        "disposition_authority",
        "retention_period",
        "disposition_instruction",
        "record_series_title",
        "record_creator",
        "record_status",
        "vital_record",
        "classified",
        "classification_level",
    }
    for key, value in kwargs.items():
        if key in allowed:
            setattr(record, key, value)
    db.commit()
    db.refresh(record)
    return record


def delete_nara_metadata(db: Session, document_id: str) -> bool:
    """Delete NARA metadata for a document. Returns True if deleted."""
    record = db.query(NaraMetadata).filter(NaraMetadata.document_id == document_id).first()
    if record is None:
        return False
    db.delete(record)
    db.commit()
    return True


def list_vital_records(db: Session) -> list[NaraMetadata]:
    """Return all documents marked as vital records."""
    return db.query(NaraMetadata).filter(NaraMetadata.vital_record.is_(True)).all()


def list_records_due_disposal(db: Session) -> list[NaraMetadata]:
    """Return all records with status 'scheduled_for_disposal'."""
    return (
        db.query(NaraMetadata)
        .filter(NaraMetadata.record_status == "scheduled_for_disposal")
        .all()
    )

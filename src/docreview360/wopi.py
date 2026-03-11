# SPDX-License-Identifier: MIT
"""WOPI host implementation for Microsoft 365 co-authoring.

Implements the WOPI protocol subset required for Office Online Server / Microsoft
365 co-authoring.  Only the operations needed for CheckFileInfo, GetFile, PutFile,
Lock, Unlock, RefreshLock, and GetLock are provided.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status

from .documents import get_document, update_document

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data-transfer objects
# ---------------------------------------------------------------------------


@dataclass
class WOPICheckFileInfo:
    """Response payload for the CheckFileInfo WOPI action."""

    BaseFileName: str
    OwnerId: str
    Size: int
    UserId: str
    Version: str
    UserFriendlyName: str
    UserCanWrite: bool = True
    UserCanNotWriteRelative: bool = True
    SupportsLocks: bool = True
    SupportsUpdate: bool = True


@dataclass
class WOPILock:
    """In-flight WOPI lock record (also persisted to SQLite)."""

    file_id: str
    lock_token: str
    locked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    locked_by: str = ""


# ---------------------------------------------------------------------------
# WOPI file-info
# ---------------------------------------------------------------------------


def get_wopi_file_info(doc_id: str, user: str) -> WOPICheckFileInfo:
    """Return WOPI CheckFileInfo metadata for *doc_id*.

    Raises ``404`` when the document does not exist.
    """
    doc = get_document(doc_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found",
        )
    content_bytes = doc.content.encode("utf-8")
    return WOPICheckFileInfo(
        BaseFileName=f"document-{doc_id[:8]}.docx",
        OwnerId=doc.user or "unknown",
        Size=len(content_bytes),
        UserId=user,
        Version=str(doc.version_number),
        UserFriendlyName=user,
        UserCanWrite=True,
        UserCanNotWriteRelative=True,
        SupportsLocks=True,
        SupportsUpdate=True,
    )


# ---------------------------------------------------------------------------
# Lock management — SQLite persistence via WOPILockRecord
# ---------------------------------------------------------------------------


def _get_lock_record(file_id: str):  # type: ignore[return]
    """Return the ORM lock record for *file_id* or ``None``."""
    try:
        from .db_store import get_db
        from .models import WOPILockRecord

        db = get_db()
        with db.orm_session() as session:
            return session.get(WOPILockRecord, file_id)
    except Exception as exc:  # pragma: no cover
        _logger.warning("WOPI lock DB read failed: %s", exc)
        return None


def get_wopi_lock(file_id: str) -> Optional[WOPILock]:
    """Return the active :class:`WOPILock` for *file_id* or ``None``."""
    try:
        from .db_store import get_db
        from .models import WOPILockRecord

        db = get_db()
        with db.orm_session() as session:
            record = session.get(WOPILockRecord, file_id)
            if record is None:
                return None
            return WOPILock(
                file_id=record.file_id,
                lock_token=record.lock_token,
                locked_at=record.locked_at,
                locked_by=record.locked_by or "",
            )
    except Exception as exc:  # pragma: no cover
        _logger.warning("WOPI get_lock DB read failed: %s", exc)
        return None


def set_wopi_lock(file_id: str, lock_token: str, user: str) -> None:
    """Acquire or refresh a WOPI lock for *file_id*.

    If the file is already locked by a *different* token raises ``HTTP 409``
    with ``X-WOPI-Lock`` set to the current token (WOPI protocol requirement).

    If the file is already locked by the *same* token this is treated as a
    RefreshLock (idempotent).
    """
    from .db_store import get_db
    from .models import WOPILockRecord

    db = get_db()
    with db.orm_session() as session:
        record = session.get(WOPILockRecord, file_id)
        now = datetime.now(timezone.utc)
        if record is None:
            record = WOPILockRecord(
                file_id=file_id,
                lock_token=lock_token,
                locked_at=now,
                locked_by=user,
            )
            session.add(record)
        elif record.lock_token != lock_token:
            # Conflict — return existing lock token in the exception detail so
            # the router can set the X-WOPI-Lock header.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=record.lock_token,
                headers={"X-WOPI-Lock": record.lock_token},
            )
        else:
            # Same token → refresh
            record.locked_at = now
            record.locked_by = user


def refresh_wopi_lock(file_id: str, lock_token: str) -> None:
    """Refresh an existing lock for *file_id*.

    Raises ``HTTP 409`` when the lock does not match or no lock exists.
    """
    from .db_store import get_db
    from .models import WOPILockRecord

    db = get_db()
    with db.orm_session() as session:
        record = session.get(WOPILockRecord, file_id)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="",
                headers={"X-WOPI-Lock": ""},
            )
        if record.lock_token != lock_token:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=record.lock_token,
                headers={"X-WOPI-Lock": record.lock_token},
            )
        record.locked_at = datetime.now(timezone.utc)


def release_wopi_lock(file_id: str, lock_token: str) -> None:
    """Release the lock for *file_id*.

    Raises ``HTTP 409`` when the supplied token does not match the current lock.
    """
    from .db_store import get_db
    from .models import WOPILockRecord

    db = get_db()
    with db.orm_session() as session:
        record = session.get(WOPILockRecord, file_id)
        if record is None:
            # Already unlocked — WOPI spec says return 200
            return
        if record.lock_token != lock_token:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=record.lock_token,
                headers={"X-WOPI-Lock": record.lock_token},
            )
        session.delete(record)


# ---------------------------------------------------------------------------
# File content I/O
# ---------------------------------------------------------------------------


def put_file_contents(doc_id: str, content: bytes, user: str) -> None:
    """Persist *content* bytes as the latest version of document *doc_id*.

    The bytes are decoded as UTF-8 text so they can be stored in the existing
    :func:`~docreview360.documents.update_document` pipeline which expects a
    ``str``.  Binary Office formats are stored as-is after encoding fallback.

    Raises ``HTTP 404`` when the document does not exist.
    """
    doc = get_document(doc_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{doc_id}' not found",
        )
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        # Store a base64 representation so binary content round-trips safely.
        import base64

        text = base64.b64encode(content).decode("ascii")

    update_document(doc_id, text, author=user)

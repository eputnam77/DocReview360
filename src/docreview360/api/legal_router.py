# SPDX-License-Identifier: MIT
"""Legal hold and eDiscovery endpoints."""

from __future__ import annotations

import tempfile
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import auth
from ..db_store import get_db
from ..rbac import require_role
from ..legal_hold import (
    add_document_to_hold,
    create_legal_hold,
    get_document_holds,
    get_legal_hold,
    is_document_on_hold,
    list_legal_holds,
    release_hold,
    remove_document_from_hold,
)
from ..ediscovery import export_ediscovery

router = APIRouter(tags=["legal"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class LegalHoldCreate(BaseModel):
    hold_name: str
    hold_reason: str | None = None


class AddDocumentsPayload(BaseModel):
    document_ids: list[str]


class EDiscoveryExportPayload(BaseModel):
    document_ids: list[str]
    include_audit: bool = True


def _hold_to_dict(hold: Any) -> dict[str, Any]:
    return {
        "id": hold.id,
        "hold_name": hold.hold_name,
        "hold_reason": hold.hold_reason,
        "created_by": hold.created_by,
        "created_at": hold.created_at.isoformat() if hold.created_at else None,
        "expires_at": hold.expires_at.isoformat() if hold.expires_at else None,
        "status": hold.status,
        "released_by": hold.released_by,
        "released_at": hold.released_at.isoformat() if hold.released_at else None,
    }


# ---------------------------------------------------------------------------
# Legal Hold endpoints
# ---------------------------------------------------------------------------


@router.post("/legal/holds")
async def create_hold(
    payload: LegalHoldCreate,
    current_user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Create a new legal hold (admin only)."""
    with get_db().orm_session() as db:
        hold = create_legal_hold(
            db,
            name=payload.hold_name,
            reason=payload.hold_reason,
            created_by=current_user.username,
        )
        return _hold_to_dict(hold)


@router.get("/legal/holds")
async def list_holds(
    status: str | None = None,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[dict[str, Any]]:
    """List legal holds, optionally filtered by status."""
    with get_db().orm_session() as db:
        holds = list_legal_holds(db, status=status)
        return [_hold_to_dict(h) for h in holds]


@router.get("/legal/holds/{hold_id}")
async def get_hold(
    hold_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Get details for a legal hold including its document list."""
    with get_db().orm_session() as db:
        hold = get_legal_hold(db, hold_id)
        if hold is None:
            raise HTTPException(status_code=404, detail="Legal hold not found")
        result = _hold_to_dict(hold)
        result["documents"] = [
            {"document_id": d.document_id, "added_by": d.added_by}
            for d in hold.documents
        ]
        return result


@router.post("/legal/holds/{hold_id}/documents")
async def add_documents_to_hold(
    hold_id: str,
    payload: AddDocumentsPayload,
    current_user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Add documents to a legal hold."""
    with get_db().orm_session() as db:
        hold = get_legal_hold(db, hold_id)
        if hold is None:
            raise HTTPException(status_code=404, detail="Legal hold not found")
        if hold.status != "active":
            raise HTTPException(status_code=409, detail="Cannot add documents to a released hold")
        added = []
        for doc_id in payload.document_ids:
            add_document_to_hold(db, hold_id, doc_id, added_by=current_user.username)
            added.append(doc_id)
        return {"added": added, "hold_id": hold_id}


@router.delete("/legal/holds/{hold_id}/documents/{document_id}")
async def remove_document_from_hold_endpoint(
    hold_id: str,
    document_id: str,
    current_user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Remove a document from a legal hold."""
    with get_db().orm_session() as db:
        removed = remove_document_from_hold(db, hold_id, document_id)
        if not removed:
            raise HTTPException(status_code=404, detail="Document not found in this hold")
        return {"removed": document_id, "hold_id": hold_id}


@router.post("/legal/holds/{hold_id}/release")
async def release_legal_hold(
    hold_id: str,
    current_user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Release a legal hold (admin only)."""
    with get_db().orm_session() as db:
        hold = get_legal_hold(db, hold_id)
        if hold is None:
            raise HTTPException(status_code=404, detail="Legal hold not found")
        if hold.status != "active":
            raise HTTPException(status_code=409, detail="Hold is not active")
        hold = release_hold(db, hold_id, released_by=current_user.username)
        return _hold_to_dict(hold)


@router.get("/documents/{doc_id}/holds")
async def get_document_holds_endpoint(
    doc_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """List active legal holds on a document."""
    with get_db().orm_session() as db:
        holds = get_document_holds(db, doc_id)
        return {
            "document_id": doc_id,
            "on_hold": len(holds) > 0,
            "holds": [_hold_to_dict(h) for h in holds],
        }


# ---------------------------------------------------------------------------
# eDiscovery export
# ---------------------------------------------------------------------------


@router.post("/legal/ediscovery/export")
async def ediscovery_export(
    payload: EDiscoveryExportPayload,
    current_user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Trigger an eDiscovery export for the specified documents."""
    if not payload.document_ids:
        raise HTTPException(status_code=422, detail="document_ids must not be empty")
    with get_db().orm_session() as db:
        tmp = tempfile.NamedTemporaryFile(
            suffix=".zip", prefix="ediscovery_", delete=False
        )
        tmp.close()
        result = export_ediscovery(
            db,
            document_ids=payload.document_ids,
            output_path=tmp.name,
            include_audit=payload.include_audit,
            exported_by=current_user.username,
        )
    return result

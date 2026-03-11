# SPDX-License-Identifier: MIT
"""Document branch and merge endpoints for parallel review tracks."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import auth
from ..db_store import get_db
from ..models import Document, DocumentBranch, DocumentVersion

router = APIRouter(prefix="/documents", tags=["branches"])


# ---------------------------------------------------------------------------
# Pydantic request/response models
# ---------------------------------------------------------------------------


class BranchCreate(BaseModel):
    branch_name: str
    source_revision_id: int | None = None
    content_snapshot: str | None = None


class BranchContentUpdate(BaseModel):
    content_snapshot: str


class BranchMerge(BaseModel):
    merge_strategy: str = "overwrite"  # "overwrite" | "append"


def _branch_to_dict(branch: DocumentBranch) -> dict[str, Any]:
    return {
        "id": branch.id,
        "document_id": branch.document_id,
        "branch_name": branch.branch_name,
        "created_by": branch.created_by,
        "created_at": branch.created_at.isoformat() if branch.created_at else None,
        "status": branch.status,
        "source_revision_id": branch.source_revision_id,
        "merged_revision_id": branch.merged_revision_id,
        "merged_by": branch.merged_by,
        "merged_at": branch.merged_at.isoformat() if branch.merged_at else None,
        "content_snapshot": branch.content_snapshot,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/{doc_id}/branches")
async def create_branch(
    doc_id: str,
    payload: BranchCreate,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Create a named branch of a document for parallel review."""
    with get_db().orm_session() as db:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if doc is None:
            raise HTTPException(status_code=404, detail="Document not found")

        # Optionally seed content from a specific revision
        snapshot = payload.content_snapshot
        if snapshot is None and payload.source_revision_id is not None:
            rev = (
                db.query(DocumentVersion)
                .filter(DocumentVersion.id == payload.source_revision_id)
                .first()
            )
            if rev is None:
                raise HTTPException(status_code=404, detail="Source revision not found")
            snapshot = rev.content

        branch = DocumentBranch(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            branch_name=payload.branch_name,
            created_by=current_user.username,
            created_at=datetime.now(timezone.utc),
            status="open",
            source_revision_id=payload.source_revision_id,
            content_snapshot=snapshot,
        )
        db.add(branch)
        db.flush()
        result = _branch_to_dict(branch)
    return result


@router.get("/{doc_id}/branches")
async def list_branches(
    doc_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[dict[str, Any]]:
    """List all branches for a document."""
    with get_db().orm_session() as db:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if doc is None:
            raise HTTPException(status_code=404, detail="Document not found")
        branches = (
            db.query(DocumentBranch)
            .filter(DocumentBranch.document_id == doc_id)
            .order_by(DocumentBranch.created_at.desc())
            .all()
        )
        return [_branch_to_dict(b) for b in branches]


@router.get("/{doc_id}/branches/{branch_id}")
async def get_branch(
    doc_id: str,
    branch_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Get details for a specific branch."""
    with get_db().orm_session() as db:
        branch = (
            db.query(DocumentBranch)
            .filter(DocumentBranch.id == branch_id, DocumentBranch.document_id == doc_id)
            .first()
        )
        if branch is None:
            raise HTTPException(status_code=404, detail="Branch not found")
        return _branch_to_dict(branch)


@router.put("/{doc_id}/branches/{branch_id}/content")
async def update_branch_content(
    doc_id: str,
    branch_id: str,
    payload: BranchContentUpdate,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Update the working content of an open branch."""
    with get_db().orm_session() as db:
        branch = (
            db.query(DocumentBranch)
            .filter(DocumentBranch.id == branch_id, DocumentBranch.document_id == doc_id)
            .first()
        )
        if branch is None:
            raise HTTPException(status_code=404, detail="Branch not found")
        if branch.status != "open":
            raise HTTPException(
                status_code=409, detail=f"Cannot update a branch with status '{branch.status}'"
            )
        branch.content_snapshot = payload.content_snapshot
        db.flush()
        return _branch_to_dict(branch)


@router.post("/{doc_id}/branches/{branch_id}/merge")
async def merge_branch(
    doc_id: str,
    branch_id: str,
    payload: BranchMerge,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Merge a branch back into the document, creating a new DocumentVersion."""
    with get_db().orm_session() as db:
        branch = (
            db.query(DocumentBranch)
            .filter(DocumentBranch.id == branch_id, DocumentBranch.document_id == doc_id)
            .first()
        )
        if branch is None:
            raise HTTPException(status_code=404, detail="Branch not found")
        if branch.status == "merged":
            raise HTTPException(status_code=409, detail="Branch is already merged")
        if branch.status == "closed":
            raise HTTPException(status_code=409, detail="Branch is closed and cannot be merged")
        if not branch.content_snapshot:
            raise HTTPException(status_code=422, detail="Branch has no content to merge")

        doc = db.query(Document).filter(Document.id == doc_id).first()
        if doc is None:
            raise HTTPException(status_code=404, detail="Document not found")

        # Determine final content
        if payload.merge_strategy == "append":
            base_content = doc.content or ""
            merged_content = base_content + "\n\n" + branch.content_snapshot
        else:
            merged_content = branch.content_snapshot

        # Create a new DocumentVersion
        new_version = DocumentVersion(document_id=doc_id, content=merged_content)
        db.add(new_version)
        db.flush()  # Get the generated ID

        # Update document content
        doc.content = merged_content

        # Mark branch as merged
        now = datetime.now(timezone.utc)
        branch.status = "merged"
        branch.merged_by = current_user.username
        branch.merged_at = now
        branch.merged_revision_id = new_version.id

        db.flush()
        result = {**_branch_to_dict(branch), "new_revision_id": new_version.id}
    return result


@router.post("/{doc_id}/branches/{branch_id}/close")
async def close_branch(
    doc_id: str,
    branch_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Close/abandon a branch without merging."""
    with get_db().orm_session() as db:
        branch = (
            db.query(DocumentBranch)
            .filter(DocumentBranch.id == branch_id, DocumentBranch.document_id == doc_id)
            .first()
        )
        if branch is None:
            raise HTTPException(status_code=404, detail="Branch not found")
        if branch.status != "open":
            raise HTTPException(
                status_code=409, detail=f"Cannot close a branch with status '{branch.status}'"
            )
        branch.status = "closed"
        db.flush()
        return _branch_to_dict(branch)

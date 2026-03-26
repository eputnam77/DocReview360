# SPDX-License-Identifier: MIT
"""Comments sub-router: project-level comment creation and retrieval (anchored comments)."""
from __future__ import annotations

import logging
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel

from .. import auth
from ..comments import add_comment, list_comments, render_comment_for_response
from ..documents import list_documents
from ..search import get_project

_logger = logging.getLogger(__name__)

router = APIRouter()


class CommentCreateRequest(BaseModel):
    """Request body for creating a project comment."""

    text: str
    document_id: Optional[str] = None
    source: str = "inline"
    parent: Optional[str] = None
    tags: Optional[list[str]] = None


def _resolve_document_id(project_id: str, document_id: Optional[str]) -> str:
    """Return a valid document ID for ``project_id``.

    If ``document_id`` is provided and belongs to the project, it is returned
    unchanged.  Otherwise the first document found for the project is used as a
    fallback so that a stale or missing ``document_id`` never produces a
    ``Document Not Found`` error.
    """
    docs = [d for d in list_documents() if d.project == project_id]
    if document_id:
        # Verify it belongs to this project
        if any(d.id == document_id for d in docs):
            return document_id
        _logger.warning(
            "document_id %r not found in project %r; falling back to first available document",
            document_id,
            project_id,
        )
    if docs:
        return docs[0].id
    # No document at all — use project_id as a synthetic key so comments are
    # at least stored rather than raising a hard error.
    return project_id


@router.post("/comments/{project_id}", status_code=201)
async def create_project_comment(
    project_id: str,
    body: CommentCreateRequest,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """Create a new anchored comment for a project.

    The ``document_id`` in the request body is optional.  When absent or stale
    the server resolves the document automatically from the project so that the
    caller never receives a ``Document Not Found`` error.
    """
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    doc_id = _resolve_document_id(project_id, body.document_id)

    try:
        comment = add_comment(
            document=doc_id,
            user=current_user.username,
            text=body.text,
            parent=body.parent,
            tags=body.tags,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Override the source to match the request (default: "inline").
    comment.source = body.source if body.source in ("inline", "feedback", "review") else "inline"

    rendered = render_comment_for_response(comment)
    return {
        "id": rendered.id,
        "document_id": doc_id,
        "project_id": project_id,
        "user": rendered.user,
        "text": rendered.text,
        "status": rendered.status,
        "source": rendered.source,
        "created": rendered.created.isoformat() if rendered.created else None,
    }


@router.get("/comments/{project_id}")
async def list_project_comments(
    project_id: str,
    skip: int = Query(0, ge=0, description="Number of comments to skip"),
    limit: int = Query(20, ge=1, le=200, description="Maximum comments to return"),
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """Return all comments for a project aggregated across its documents, with pagination.

    Each comment includes a ``source`` field (``"inline"`` or ``"feedback"``) and a
    ``source_label`` badge string for display.

    Response shape: ``{ items: [...], total: N, skip: 0, limit: 20 }``
    """
    from ..pagination import PaginatedResponse

    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    docs = [d for d in list_documents() if d.project == project_id]
    # Collect all document IDs to query, including the synthetic project_id key
    # used when comments were posted without any associated document.
    doc_id_to_label: dict[str, str] = {doc.id: doc.id for doc in docs}
    # Also check comments stored directly under the project_id key (no-document path)
    doc_id_to_label[project_id] = project_id
    seen_ids: set[str] = set()
    all_comments: list[dict] = []
    for doc_key in doc_id_to_label:
        for raw in list_comments(doc_key):
            if raw.id in seen_ids:
                continue
            seen_ids.add(raw.id)
            comment = render_comment_for_response(raw)
            source = getattr(comment, "source", "inline") or "inline"
            source_label = "Anchored" if source == "inline" else source.capitalize()
            item = {
                "id": comment.id,
                "document_id": doc_key,
                "user": comment.user,
                "text": comment.text,
                "status": comment.status,
                "source": source,
                "source_label": source_label,
                "created": comment.created.isoformat() if comment.created else None,
            }
            all_comments.append(item)

    page = PaginatedResponse.from_sequence(all_comments, skip=skip, limit=limit)
    return {
        "items": page.items,
        "total": page.total,
        "skip": page.skip,
        "limit": page.limit,
    }


@router.get("/comments/{project_id}/export/docx")
async def export_comments_docx(
    project_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> Response:
    """Export all comments for a project as a Word (.docx) document.

    Collects comments from every document that belongs to ``project_id`` and
    writes them into a single Word file grouped by document.  Falls back to a
    plain-text response if ``python-docx`` is not installed.
    """
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    docs = [d for d in list_documents() if d.project == project_id]

    try:
        from docx import Document as _DocxDocument  # type: ignore[import-untyped]
        from docx.shared import Pt  # type: ignore[import-untyped]

        docx_doc = _DocxDocument()
        docx_doc.add_heading(f"Comments — {project.name or project_id}", level=1)

        total_comments = 0
        for document in docs:
            raw_comments = list_comments(document.id)
            if not raw_comments:
                continue
            docx_doc.add_heading(document.id, level=2)
            for raw in raw_comments:
                comment = render_comment_for_response(raw)
                date_str = (
                    comment.created.strftime("%Y-%m-%d")
                    if comment.created
                    else "unknown date"
                )
                para = docx_doc.add_paragraph()
                run_meta = para.add_run(f"[{comment.status or 'open'}] {comment.user} — {date_str}: ")
                run_meta.font.size = Pt(9)
                run_meta.bold = True
                para.add_run(comment.text or "")
                total_comments += 1

        if total_comments == 0:
            docx_doc.add_paragraph("No comments found for this project.")

        buf = BytesIO()
        docx_doc.save(buf)
        content = buf.getvalue()
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = f"comments_{project_id}.docx"

    except ImportError:
        _logger.warning("python-docx not available; falling back to plain text export")
        lines: list[str] = [f"Comments for project: {project.name or project_id}\n\n"]
        for document in docs:
            raw_comments = list_comments(document.id)
            if not raw_comments:
                continue
            lines.append(f"Document: {document.id}\n")
            for raw in raw_comments:
                comment = render_comment_for_response(raw)
                date_str = (
                    comment.created.strftime("%Y-%m-%d") if comment.created else "unknown date"
                )
                lines.append(
                    f"  [{comment.status or 'open'}] {comment.user} ({date_str}): {comment.text or ''}\n"
                )
            lines.append("\n")
        content = "".join(lines).encode("utf-8")
        media_type = "text/plain; charset=utf-8"
        filename = f"comments_{project_id}.txt"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

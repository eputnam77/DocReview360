# SPDX-License-Identifier: MIT
"""Comments sub-router: export endpoints for project-level comment collections."""
from __future__ import annotations

import logging
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from .. import auth
from ..comments import list_comments, render_comment_for_response
from ..documents import list_documents
from ..search import get_project

_logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/comments/{project_id}")
async def list_project_comments(
    project_id: str,
    skip: int = Query(0, ge=0, description="Number of comments to skip"),
    limit: int = Query(20, ge=1, le=200, description="Maximum comments to return"),
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """Return all comments for a project aggregated across its documents, with pagination.

    Response shape: ``{ items: [...], total: N, skip: 0, limit: 20 }``
    """
    from ..pagination import PaginatedResponse

    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    docs = [d for d in list_documents() if d.project == project_id]
    all_comments: list[dict] = []
    for doc in docs:
        for raw in list_comments(doc.id):
            comment = render_comment_for_response(raw)
            item = {
                "id": comment.id,
                "document_id": doc.id,
                "user": comment.user,
                "text": comment.text,
                "status": comment.status,
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

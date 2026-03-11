# SPDX-License-Identifier: MIT
"""Feedback ledger sub-router — /projects/{id}/feedback/* (Item 44 Phase 3)."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel

from .. import auth
from ..feedback_ledger import (
    FeedbackItem,
    FeedbackProgress,
    FEEDBACK_STATUSES,
    FEEDBACK_TYPES,
    TERMINAL_FEEDBACK_STATUSES,
    create_feedback_item,
    dispose_feedback_item,
    get_feedback_item,
    get_feedback_progress,
    list_feedback_items,
    mark_question_satisfied,
    reply_to_feedback,
)
from ..search import get_project

_logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------


class FeedbackCreate(BaseModel):
    text: str
    feedback_type: str = "comment"
    assignment_id: Optional[str] = None
    phase: Optional[str] = None
    tags: list[str] = []


class DispositionBody(BaseModel):
    status: str  # accepted | rejected | resolved
    reason: Optional[str] = None


class ReplyBody(BaseModel):
    text: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_project_or_404(project_id: str):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _get_item_or_404(item_id: str) -> FeedbackItem:
    item = get_feedback_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Feedback item not found")
    return item


def _require_project_access(project, current_user: auth.User) -> None:
    from .projects_router import _enforce_project_access
    _enforce_project_access(project, current_user)


def _require_manage_access(project, current_user: auth.User) -> None:
    from .projects_router import _enforce_project_manage_access
    _enforce_project_manage_access(project, current_user)


def _emit_feedback_notification(event: str, item: FeedbackItem, project) -> None:
    """Fire-and-forget notification for feedback conversation events."""
    try:
        from ..notifications import send_notification
        messages: dict[str, str] = {
            "review.question_asked": (
                f"Reviewer '{item.reviewer}' has asked a question on project "
                f"'{project.name}'. /projects/{project.id}#feedback"
            ),
            "review.question_answered": (
                f"Your question on project '{project.name}' has been answered. "
                f"/projects/{project.id}#feedback"
            ),
        }
        msg = messages.get(event, f"Feedback event '{event}' on project '{project.name}'.")
        send_notification(event, message=msg, project_id=project.id, reviewer=item.reviewer)
    except Exception as exc:  # pragma: no cover
        _logger.debug("Feedback notification suppressed: %s", exc)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/projects/{project_id}/feedback")
async def list_project_feedback(
    project_id: str,
    reviewer: Optional[str] = Query(default=None),
    feedback_type: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    phase: Optional[str] = Query(default=None),
    assignment_id: Optional[str] = Query(default=None),
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[dict]:
    """List feedback items for a project, with optional filters."""
    project = _get_project_or_404(project_id)
    _require_project_access(project, current_user)
    items = list_feedback_items(
        project_id,
        reviewer=reviewer,
        feedback_type=feedback_type,
        status=status,
        phase=phase,
        assignment_id=assignment_id,
    )
    return [i.model_dump() for i in items]


@router.post("/projects/{project_id}/feedback", status_code=201)
async def create_project_feedback(
    project_id: str,
    body: FeedbackCreate,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """Create a new feedback item (reviewer posts feedback)."""
    project = _get_project_or_404(project_id)
    _require_project_access(project, current_user)
    if body.feedback_type not in FEEDBACK_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"feedback_type must be one of {FEEDBACK_TYPES}",
        )
    item = create_feedback_item(
        project_id,
        current_user.username,
        body.text,
        assignment_id=body.assignment_id,
        feedback_type=body.feedback_type,
        phase=body.phase,
        tags=body.tags,
    )
    # Notify SME when a question is asked
    if body.feedback_type == "question":
        _emit_feedback_notification("review.question_asked", item, project)
    return item.model_dump()


@router.put("/projects/{project_id}/feedback/{item_id}/disposition")
async def disposition_feedback_item(
    project_id: str,
    item_id: str,
    body: DispositionBody,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """SME dispositions a feedback item (accept / reject / resolve)."""
    project = _get_project_or_404(project_id)
    _require_manage_access(project, current_user)
    item = _get_item_or_404(item_id)
    if item.project_id != project_id:
        raise HTTPException(status_code=404, detail="Feedback item not found")
    if body.status not in TERMINAL_FEEDBACK_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"status must be one of {sorted(TERMINAL_FEEDBACK_STATUSES)}",
        )
    updated = dispose_feedback_item(
        item_id,
        body.status,
        disposition_by=current_user.username,
        disposition_reason=body.reason,
    )
    return updated.model_dump()


@router.post("/projects/{project_id}/feedback/{item_id}/reply", status_code=201)
async def reply_to_project_feedback(
    project_id: str,
    item_id: str,
    body: ReplyBody,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """Post a threaded reply to a feedback item."""
    project = _get_project_or_404(project_id)
    _require_project_access(project, current_user)
    parent = _get_item_or_404(item_id)
    if parent.project_id != project_id:
        raise HTTPException(status_code=404, detail="Feedback item not found")
    reply = reply_to_feedback(item_id, current_user.username, body.text)
    # If SME answered a reviewer's question, notify the reviewer
    if parent.feedback_type == "question" and current_user.username != parent.reviewer:
        _emit_feedback_notification("review.question_answered", parent, project)
    return reply.model_dump()


@router.post("/projects/{project_id}/feedback/{item_id}/question-satisfied")
async def mark_feedback_question_satisfied(
    project_id: str,
    item_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """Reviewer marks a 'question' type item as satisfied."""
    _get_project_or_404(project_id)
    item = _get_item_or_404(item_id)
    if item.project_id != project_id:
        raise HTTPException(status_code=404, detail="Feedback item not found")
    if item.feedback_type != "question":
        raise HTTPException(status_code=422, detail="Only 'question' items can be marked satisfied")
    if current_user.username != item.reviewer:
        raise HTTPException(status_code=403, detail="Only the original reviewer can mark this satisfied")
    updated = mark_question_satisfied(item_id)
    return updated.model_dump()


@router.get("/projects/{project_id}/feedback/progress")
async def get_project_feedback_progress(
    project_id: str,
    phase: Optional[str] = Query(default=None),
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """Return aggregate feedback progress counts for a project."""
    project = _get_project_or_404(project_id)
    _require_project_access(project, current_user)
    progress = get_feedback_progress(project_id, phase=phase)
    return progress.model_dump()

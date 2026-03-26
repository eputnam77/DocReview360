# SPDX-License-Identifier: MIT
"""Feedback ledger sub-router — /projects/{id}/feedback/* (Item 44 Phase 3)."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field, field_validator

from .. import auth
from ..logs import log_event
from ..feedback_ledger import (
    FeedbackItem,
    FeedbackProgress,
    FEEDBACK_STATUSES,
    FEEDBACK_TYPES,
    TERMINAL_FEEDBACK_STATUSES,
    archive_phase_feedback,
    create_feedback_item,
    dispose_feedback_item,
    get_feedback_item,
    get_feedback_progress,
    list_feedback_items,
    list_feedback_phases,
    mark_question_satisfied,
    reply_to_feedback,
)
from ..search import get_project

_logger = logging.getLogger(__name__)
router = APIRouter()


def _emit_webhook(event: str, data: dict) -> None:
    """Best-effort lifecycle webhook emission — never raises."""
    try:
        from .webhooks import emit_lifecycle_event
        emit_lifecycle_event(event, data)  # type: ignore[arg-type]
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------


class FeedbackCreate(BaseModel):
    text: str = Field(min_length=1, max_length=10_000)
    feedback_type: str = Field(default="comment", min_length=1, max_length=50)
    assignment_id: Optional[str] = Field(default=None, max_length=100)
    phase: Optional[str] = Field(default=None, max_length=100)
    tags: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("feedback_type")
    @classmethod
    def type_must_be_known(cls, v: str) -> str:
        if v not in FEEDBACK_TYPES:
            raise ValueError(f"feedback_type must be one of {sorted(FEEDBACK_TYPES)}")
        return v

    @field_validator("tags")
    @classmethod
    def tags_not_blank(cls, v: list[str]) -> list[str]:
        if any(not t.strip() for t in v):
            raise ValueError("tags must not contain blank entries")
        return [t.strip()[:100] for t in v]


class DispositionBody(BaseModel):
    status: str = Field(min_length=1, max_length=50)  # accepted | rejected | resolved
    reason: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("status")
    @classmethod
    def status_must_be_valid(cls, v: str) -> str:
        valid = FEEDBACK_STATUSES - {"open"}
        if v not in valid:
            raise ValueError(f"status must be one of {sorted(valid)}")
        return v


class ReplyBody(BaseModel):
    text: str = Field(min_length=1, max_length=10_000)


class ArchivePhaseBody(BaseModel):
    phase: str = Field(min_length=1, max_length=100)


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
    """Allow access if user passes standard project access OR is an assignment reviewer."""
    from .projects_router import _is_admin_user
    if _is_admin_user(current_user):
        return
    # Check if user is an assignment-based reviewer on this project
    from ..review_assignments import list_assignments as _list_assignments
    if any(a.reviewer == current_user.username for a in _list_assignments(project.id)):
        return
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
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(20, ge=1, le=200, description="Maximum items to return"),
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """List feedback items for a project, with optional filters and pagination.

    Response shape: ``{ items: [...], total: N, skip: 0, limit: 20 }``
    """
    from ..pagination import PaginatedResponse

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
    page = PaginatedResponse.from_sequence(items, skip=skip, limit=limit)
    return {
        "items": [i.model_dump() for i in page.items],
        "total": page.total,
        "skip": page.skip,
        "limit": page.limit,
    }


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
    log_event(
        "feedback.submitted",
        user_id=current_user.username,
        entity_id=project_id,
        entity_type="project",
        feedback_id=item.id,
        feedback_type=item.feedback_type,
        assignment_id=item.assignment_id,
    )
    _emit_webhook("feedback.submitted", {
        "project_id": project_id,
        "feedback_id": item.id,
        "feedback_type": item.feedback_type,
        "reviewer": current_user.username,
    })
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
    log_event(
        "feedback.dispositioned",
        user_id=current_user.username,
        entity_id=project_id,
        entity_type="project",
        feedback_id=item_id,
        feedback_type=item.feedback_type,
        disposition=body.status,
        reason=body.reason,
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
    log_event(
        "feedback.replied",
        user_id=current_user.username,
        entity_id=project_id,
        entity_type="project",
        feedback_id=item_id,
        reply_id=reply.id,
    )
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


@router.get("/projects/{project_id}/feedback/phases")
async def get_project_feedback_phases(
    project_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[str]:
    """Return distinct phases that have feedback items for a project."""
    project = _get_project_or_404(project_id)
    _require_project_access(project, current_user)
    return list_feedback_phases(project_id)


@router.post("/projects/{project_id}/feedback/archive-phase")
async def archive_project_phase_feedback(
    project_id: str,
    body: ArchivePhaseBody,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """Archive (resolve) all open feedback items in a given phase.

    Called automatically (or manually by the SME) when a phase advances.
    Archived items become read-only (status=resolved with archive reason).
    Returns the number of items archived.
    """
    project = _get_project_or_404(project_id)
    _require_manage_access(project, current_user)
    count = archive_phase_feedback(
        project_id, body.phase, archived_by=current_user.username
    )
    log_event(
        "feedback.phase_archived",
        user_id=current_user.username,
        entity_id=project_id,
        entity_type="project",
        phase=body.phase,
        archived_count=count,
    )
    return {"archived": count, "phase": body.phase}

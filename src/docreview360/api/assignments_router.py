# SPDX-License-Identifier: MIT
"""Review assignment sub-router — /projects/{id}/assignments/* (Item 44)."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel

from .. import auth
from ..review_assignments import (
    ReviewAssignmentModel,
    TERMINAL_STATUSES,
    create_assignment,
    delete_assignment,
    get_assignment,
    list_assignments,
    migrate_reviewers_to_assignments,
    replace_assignment,
    transition_status,
    _update_fields,
)
from ..search import get_project

_logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic request bodies
# ---------------------------------------------------------------------------


class AssignmentCreate(BaseModel):
    reviewer: str
    due_date: datetime | None = None


class AssignmentUpdate(BaseModel):
    due_date: datetime | None = None


class ReplaceBody(BaseModel):
    replacement_reviewer: str
    reason: str
    due_date: datetime | None = None


class NonConcurBody(BaseModel):
    reason: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_project_or_404(project_id: str):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _get_assignment_or_404(assignment_id: str) -> ReviewAssignmentModel:
    a = get_assignment(assignment_id)
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return a


def _require_project_access(project, current_user: auth.User) -> None:
    from .projects_router import _enforce_project_access
    _enforce_project_access(project, current_user)


def _require_manage_access(project, current_user: auth.User) -> None:
    from .projects_router import _enforce_project_manage_access
    _enforce_project_manage_access(project, current_user)


def _emit_review_notification(
    event: str,
    assignment: ReviewAssignmentModel,
    project: Any,
) -> None:
    """Fire-and-forget notification for review lifecycle events (with deep links + log)."""
    deep_link = f"/projects/{project.id}#reviewers"
    try:
        from ..notifications import send_notification

        messages: dict[str, str] = {
            "review.assigned": (
                f"You have been invited to review project '{project.name}'. "
                f"Due: {assignment.due_date or 'not set'}. {deep_link}"
            ),
            "review.feedback_received": (
                f"Reviewer '{assignment.reviewer}' has submitted feedback on "
                f"project '{project.name}'. {deep_link}"
            ),
            "review.signed": (
                f"Reviewer '{assignment.reviewer}' has concurred on "
                f"project '{project.name}'. {deep_link}"
            ),
            "review.replaced": (
                f"You have been replaced as reviewer on project '{project.name}'. "
                f"{deep_link}"
            ),
            "review.non_concurred": (
                f"Reviewer '{assignment.reviewer}' has non-concurred on "
                f"project '{project.name}'. {deep_link}"
            ),
            "review.all_complete": (
                f"All reviewers have completed their review of project '{project.name}'. "
                f"{deep_link}"
            ),
            "review.reminder": (
                f"Reminder: your review of project '{project.name}' is "
                f"due {assignment.due_date or 'soon'}. {deep_link}"
            ),
        }
        message = messages.get(event, f"Review event '{event}' on project '{project.name}'.")
        send_notification(event, message=message, project_id=project.id, reviewer=assignment.reviewer)

        # Persist to notification log (best-effort)
        try:
            from ..notification_log import log_notification
            log_notification(
                event,
                message,
                project_id=project.id,
                reviewer=assignment.reviewer,
            )
        except Exception:  # pragma: no cover
            pass
    except Exception as exc:  # pragma: no cover — best-effort
        _logger.debug("Review notification suppressed: %s", exc)


def _check_all_complete(project_id: str, project: Any) -> bool:
    """Emit review.all_complete if every non-replaced assignment is in a sign-off state."""
    assignments = list_assignments(project_id)
    active = [a for a in assignments if a.status != "replaced"]
    if not active:
        return False
    all_done = all(a.status in ("concurred", "signed") for a in active)
    if all_done:
        # Create a synthetic "all_complete" assignment object for the notification
        first = active[0]
        _emit_review_notification("review.all_complete", first, project)
    return all_done


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/projects/{project_id}/assignments")
async def list_project_assignments(
    project_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[dict]:
    """List all reviewer assignments for a project.

    On first access, migrates any bare ``reviewers`` list to ``ReviewAssignment``
    records in ``"reviewing"`` status for backward compatibility.
    """
    project = _get_project_or_404(project_id)
    _require_project_access(project, current_user)
    assignments = list_assignments(project_id)
    # Auto-migrate existing bare reviewer list on first access.
    if not assignments and getattr(project, "reviewers", None):
        assignments = migrate_reviewers_to_assignments(project_id, project.reviewers)
    return [a.model_dump() for a in assignments]


@router.post("/projects/{project_id}/assignments", status_code=201)
async def create_project_assignment(
    project_id: str,
    body: AssignmentCreate,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """Create a new reviewer assignment and notify the reviewer."""
    project = _get_project_or_404(project_id)
    _require_manage_access(project, current_user)
    assignment = create_assignment(project_id, body.reviewer, due_date=body.due_date)
    _emit_review_notification("review.assigned", assignment, project)
    return assignment.model_dump()


@router.put("/projects/{project_id}/assignments/{assignment_id}")
async def update_project_assignment(
    project_id: str,
    assignment_id: str,
    body: AssignmentUpdate,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """Update mutable fields (currently: due_date) on an assignment."""
    project = _get_project_or_404(project_id)
    _require_manage_access(project, current_user)
    assignment = _get_assignment_or_404(assignment_id)
    updates: dict[str, Any] = {}
    if body.due_date is not None:
        updates["due_date"] = body.due_date.isoformat()
    if not updates:
        return assignment.model_dump()
    return _update_fields(assignment_id, **updates).model_dump()


@router.post("/projects/{project_id}/assignments/{assignment_id}/start")
async def start_assignment(
    project_id: str,
    assignment_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """Reviewer acknowledges the assignment; transitions status to 'reviewing'."""
    _get_project_or_404(project_id)
    assignment = _get_assignment_or_404(assignment_id)
    if assignment.reviewer != current_user.username:
        raise HTTPException(status_code=403, detail="Only the assigned reviewer can start the review")
    if assignment.status != "invited":
        raise HTTPException(
            status_code=409, detail=f"Cannot start from status '{assignment.status}'"
        )
    return transition_status(assignment_id, "reviewing", ts_field="started_at").model_dump()


@router.post("/projects/{project_id}/assignments/{assignment_id}/submit")
async def submit_assignment(
    project_id: str,
    assignment_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """Reviewer marks feedback done; transitions to 'feedback_submitted'."""
    project = _get_project_or_404(project_id)
    assignment = _get_assignment_or_404(assignment_id)
    if assignment.reviewer != current_user.username:
        raise HTTPException(
            status_code=403, detail="Only the assigned reviewer can submit feedback"
        )
    if assignment.status not in ("reviewing", "invited"):
        raise HTTPException(
            status_code=409, detail=f"Cannot submit from status '{assignment.status}'"
        )
    result = transition_status(assignment_id, "feedback_submitted", ts_field="completed_at")
    _emit_review_notification("review.feedback_received", result, project)
    return result.model_dump()


@router.post("/projects/{project_id}/assignments/{assignment_id}/concur")
async def concur_assignment(
    project_id: str,
    assignment_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """Reviewer concurs; transitions to 'concurred'."""
    project = _get_project_or_404(project_id)
    assignment = _get_assignment_or_404(assignment_id)
    if assignment.reviewer != current_user.username:
        raise HTTPException(status_code=403, detail="Only the assigned reviewer can concur")
    result = transition_status(assignment_id, "concurred", ts_field="signed_at")
    _emit_review_notification("review.signed", result, project)
    _check_all_complete(project_id, project)
    return result.model_dump()


@router.post("/projects/{project_id}/assignments/{assignment_id}/non-concur")
async def non_concur_assignment(
    project_id: str,
    assignment_id: str,
    body: NonConcurBody,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """Reviewer does not concur; requires a written reason."""
    project = _get_project_or_404(project_id)
    assignment = _get_assignment_or_404(assignment_id)
    if assignment.reviewer != current_user.username:
        raise HTTPException(status_code=403, detail="Only the assigned reviewer can non-concur")
    result = _update_fields(assignment_id, status="non_concurred", replacement_reason=body.reason)
    _emit_review_notification("review.non_concurred", result, project)
    return result.model_dump()


@router.post("/projects/{project_id}/assignments/{assignment_id}/replace")
async def replace_project_assignment(
    project_id: str,
    assignment_id: str,
    body: ReplaceBody,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """Replace a reviewer (e.g. OOO); creates a new assignment for the replacement."""
    project = _get_project_or_404(project_id)
    _require_manage_access(project, current_user)
    original, new_assignment = replace_assignment(
        assignment_id, body.replacement_reviewer, body.reason, due_date=body.due_date
    )
    _emit_review_notification("review.replaced", original, project)
    _emit_review_notification("review.assigned", new_assignment, project)
    return {"original": original.model_dump(), "replacement": new_assignment.model_dump()}


@router.get("/projects/{project_id}/notification-log")
async def get_project_notification_log(
    project_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[dict]:
    """Return recent notification log entries for a project."""
    project = _get_project_or_404(project_id)
    _require_project_access(project, current_user)
    try:
        from ..notification_log import list_notification_log
        entries = list_notification_log(project_id, limit=limit)
        return [e.model_dump() for e in entries]
    except Exception as exc:
        _logger.debug("Notification log read failed: %s", exc)
        return []


@router.post("/projects/{project_id}/assignments/{assignment_id}/remind")
async def remind_reviewer(
    project_id: str,
    assignment_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """Send a manual reminder notification to a reviewer about their pending assignment."""
    project = _get_project_or_404(project_id)
    _require_manage_access(project, current_user)
    assignment = _get_assignment_or_404(assignment_id)
    if assignment.status in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot remind a reviewer in terminal status '{assignment.status}'",
        )
    _emit_review_notification("review.reminder", assignment, project)
    return {"ok": True, "assignment_id": assignment_id}


@router.delete("/projects/{project_id}/assignments/{assignment_id}", status_code=204)
async def delete_project_assignment(
    project_id: str,
    assignment_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> Response:
    """Remove an assignment.  Only valid for 'invited' status with no feedback submitted."""
    project = _get_project_or_404(project_id)
    _require_manage_access(project, current_user)
    assignment = _get_assignment_or_404(assignment_id)
    if assignment.status != "invited":
        raise HTTPException(
            status_code=409,
            detail="Can only remove assignments in 'invited' status with no feedback submitted",
        )
    delete_assignment(assignment_id)
    return Response(status_code=204)

# SPDX-License-Identifier: MIT
"""Review assignment sub-router — /projects/{id}/assignments/* (Item 44)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from datetime import datetime as _datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel

from .. import auth
from ..logs import log_event
from ..review_assignments import (
    TERMINAL_STATUSES,
    ReviewAssignmentModel,
    _update_fields,
    create_assignment,
    delete_assignment,
    get_assignment,
    list_assignments,
    migrate_reviewers_to_assignments,
    replace_assignment,
    transition_status,
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


class SignInternalBody(BaseModel):
    note: str | None = None


class ConcurWithCommentsBody(BaseModel):
    text: str


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
    """Allow access if user passes standard project access OR is an assignment reviewer."""
    from .projects_router import _is_admin_user
    if _is_admin_user(current_user):
        return
    # Check if user is an assignment-based reviewer on this project
    assignments = list_assignments(project.id)
    if any(a.reviewer == current_user.username for a in assignments):
        return
    # Fall back to standard project access check
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
            "review.started": (
                f"Reviewer '{assignment.reviewer}' has opened project '{project.name}'. "
                f"{deep_link}"
            ),
            "review.concurrence_requested": (
                f"Your concurrence has been requested on project '{project.name}'. "
                f"Please review all feedback and concur or non-concur. {deep_link}"
            ),
        }
        message = messages.get(event, f"Review event '{event}' on project '{project.name}'.")
        send_notification(
            event,
            recipient_username=assignment.reviewer,
            message=message,
            project_id=project.id,
            reviewer=assignment.reviewer,
        )

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
    log_event(
        "review.assigned",
        user_id=current_user.username,
        entity_id=project_id,
        entity_type="project",
        reviewer=assignment.reviewer,
        assignment_id=assignment.id,
    )
    _emit_webhook("review.assigned", {
        "project_id": project_id,
        "assignment_id": assignment.id,
        "reviewer": assignment.reviewer,
    })
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
    result = transition_status(assignment_id, "reviewing", ts_field="started_at")
    log_event(
        "review.status_changed",
        user_id=current_user.username,
        entity_id=project_id,
        entity_type="project",
        assignment_id=assignment_id,
        old_status="invited",
        new_status="reviewing",
    )
    return result.model_dump()


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
    log_event(
        "review.submitted",
        user_id=current_user.username,
        entity_id=project_id,
        entity_type="project",
        assignment_id=assignment_id,
        reviewer=assignment.reviewer,
    )
    _emit_webhook("review.submitted", {
        "project_id": project_id,
        "assignment_id": assignment_id,
        "reviewer": assignment.reviewer,
    })
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
    log_event(
        "review.completed",
        user_id=current_user.username,
        entity_id=project_id,
        entity_type="project",
        assignment_id=assignment_id,
        reviewer=assignment.reviewer,
        outcome="concurred",
    )
    _emit_webhook("review.completed", {
        "project_id": project_id,
        "assignment_id": assignment_id,
        "reviewer": assignment.reviewer,
        "outcome": "concurred",
    })
    return result.model_dump()


@router.post("/projects/{project_id}/assignments/{assignment_id}/concur-with-comments")
async def concur_assignment_with_comments(
    project_id: str,
    assignment_id: str,
    body: ConcurWithCommentsBody,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """Reviewer concurs and attaches final notes; transitions to 'concurred'.

    Creates a 'comment' feedback item containing the reviewer's final notes
    before transitioning the assignment to 'concurred'.
    """
    project = _get_project_or_404(project_id)
    assignment = _get_assignment_or_404(assignment_id)
    if assignment.reviewer != current_user.username:
        raise HTTPException(status_code=403, detail="Only the assigned reviewer can concur")
    # Persist the reviewer's closing comment
    from ..feedback_ledger import create_feedback_item
    create_feedback_item(
        project_id,
        current_user.username,
        body.text,
        assignment_id=assignment_id,
        feedback_type="comment",
    )
    result = transition_status(assignment_id, "concurred", ts_field="signed_at")
    _emit_review_notification("review.signed", result, project)
    _check_all_complete(project_id, project)
    log_event(
        "review.completed",
        user_id=current_user.username,
        entity_id=project_id,
        entity_type="project",
        assignment_id=assignment_id,
        reviewer=assignment.reviewer,
        outcome="concurred_with_comments",
    )
    _emit_webhook("review.completed", {
        "project_id": project_id,
        "assignment_id": assignment_id,
        "reviewer": assignment.reviewer,
        "outcome": "concurred_with_comments",
    })
    return result.model_dump()


@router.post("/projects/{project_id}/assignments/{assignment_id}/request-concurrence")
async def request_concurrence(
    project_id: str,
    assignment_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """SME requests concurrence from a reviewer (fires review.concurrence_requested notification).

    Does not change the assignment status — it only sends the notification.
    """
    project = _get_project_or_404(project_id)
    _require_manage_access(project, current_user)
    assignment = _get_assignment_or_404(assignment_id)
    if assignment.status in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot request concurrence from a reviewer in terminal status '{assignment.status}'",
        )
    _emit_review_notification("review.concurrence_requested", assignment, project)
    log_event(
        "review.concurrence_requested",
        user_id=current_user.username,
        entity_id=project_id,
        entity_type="project",
        assignment_id=assignment_id,
        reviewer=assignment.reviewer,
    )
    return {"ok": True, "assignment_id": assignment_id}


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
    log_event(
        "review.status_changed",
        user_id=current_user.username,
        entity_id=project_id,
        entity_type="project",
        assignment_id=assignment_id,
        reviewer=assignment.reviewer,
        new_status="non_concurred",
        reason=body.reason,
    )
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
    log_event(
        "review.replaced",
        user_id=current_user.username,
        entity_id=project_id,
        entity_type="project",
        original_assignment_id=assignment_id,
        original_reviewer=original.reviewer,
        replacement_reviewer=body.replacement_reviewer,
        reason=body.reason,
    )
    return {"original": original.model_dump(), "replacement": new_assignment.model_dump()}


@router.get("/projects/{project_id}/review-summary")
async def get_project_review_summary(
    project_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """Return aggregate review state for lifecycle stepper and all-complete banner."""
    project = _get_project_or_404(project_id)
    _require_project_access(project, current_user)
    from ..concurrence_gate import get_review_summary
    summary = get_review_summary(project_id)
    return summary.model_dump()


@router.get("/projects/{project_id}/assignments/me")
async def get_my_assignments(
    project_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[dict]:
    """Return the current user's assignments on this project.

    Open to any authenticated user — each user sees only their own assignments,
    so returning an empty list is safe for users without any assignments.
    """
    _get_project_or_404(project_id)  # 404 if project doesn't exist
    all_assignments = list_assignments(project_id)
    mine = [a for a in all_assignments if a.reviewer == current_user.username]
    return [a.model_dump() for a in mine]


@router.post("/projects/{project_id}/assignments/view")
async def mark_assignments_viewed(
    project_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """Auto-transition the current user's 'invited' assignments to 'reviewing'.

    Called when a reviewer opens the project view for the first time.
    Idempotent — safe to call on every page load.
    Open to any authenticated user; only transitions assignments where reviewer == current_user.
    """
    project = _get_project_or_404(project_id)
    all_assignments = list_assignments(project_id)
    started: list[str] = []
    for a in all_assignments:
        if a.reviewer == current_user.username and a.status == "invited":
            transition_status(a.id, "reviewing", ts_field="started_at")
            started.append(a.id)
            _emit_review_notification("review.started", a, project)
            log_event(
                "review.status_changed",
                user_id=current_user.username,
                entity_id=project_id,
                entity_type="project",
                assignment_id=a.id,
                old_status="invited",
                new_status="reviewing",
                trigger="view",
            )
    return {"started": started}


@router.get("/projects/{project_id}/assignments/{assignment_id}/eligibility")
async def get_assignment_eligibility(
    project_id: str,
    assignment_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """Check whether a reviewer is eligible to concur (all feedback terminal)."""
    project = _get_project_or_404(project_id)
    _require_project_access(project, current_user)
    _get_assignment_or_404(assignment_id)
    from ..concurrence_gate import check_concurrence_eligibility
    result = check_concurrence_eligibility(project_id, assignment_id)
    return result.model_dump()


@router.post("/projects/{project_id}/assignments/{assignment_id}/sign-internal")
async def sign_assignment_internally(
    project_id: str,
    assignment_id: str,
    body: SignInternalBody,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """Internal acknowledgement sign-off (checkbox + timestamp) for low-ceremony reviews.

    Transitions assignment to 'signed' and stamps signed_at.
    """
    project = _get_project_or_404(project_id)
    assignment = _get_assignment_or_404(assignment_id)
    if assignment.reviewer != current_user.username:
        raise HTTPException(status_code=403, detail="Only the assigned reviewer can sign")
    if assignment.status not in ("concurred", "feedback_submitted", "reviewing", "invited"):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot sign from status '{assignment.status}'",
        )
    update_kwargs: dict[str, Any] = {"status": "signed"}
    now = _datetime.now(UTC).isoformat()
    update_kwargs["signed_at"] = now
    if body.note:
        update_kwargs["replacement_reason"] = f"[internal-ack] {body.note}"
    result = _update_fields(assignment_id, **update_kwargs)
    _emit_review_notification("review.signed", result, project)
    _check_all_complete(project_id, project)
    log_event(
        "review.completed",
        user_id=current_user.username,
        entity_id=project_id,
        entity_type="project",
        assignment_id=assignment_id,
        reviewer=assignment.reviewer,
        outcome="signed",
    )
    _emit_webhook("review.completed", {
        "project_id": project_id,
        "assignment_id": assignment_id,
        "reviewer": assignment.reviewer,
        "outcome": "signed",
    })
    return result.model_dump()


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


@router.delete("/projects/{project_id}/assignments/{assignment_id}", status_code=204, response_model=None)
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
    reviewer = assignment.reviewer
    delete_assignment(assignment_id)
    log_event(
        "review.assignment_deleted",
        user_id=current_user.username,
        entity_id=project_id,
        entity_type="project",
        assignment_id=assignment_id,
        reviewer=reviewer,
    )
    return Response(status_code=204)

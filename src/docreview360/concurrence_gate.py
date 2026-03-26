# SPDX-License-Identifier: MIT
"""Concurrence gate — eligibility checks and review summary (Item 44 Phase 4)."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel

from .review_assignments import (
    TERMINAL_STATUSES,
    ReviewAssignmentModel,
    get_assignment,
    list_assignments,
)

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ConcurrenceEligibility(BaseModel):
    """Whether a reviewer is eligible to concur on a project."""

    eligible: bool
    open_items: int
    unanswered_questions: int
    total_feedback: int
    reason: Optional[str] = None  # human-readable explanation when not eligible


class ReviewSummary(BaseModel):
    """Aggregate review state for a project — drives lifecycle stepper + banner."""

    total_active: int
    invited: int
    reviewing: int
    feedback_submitted: int
    concurred: int
    non_concurred: int
    signed: int
    declined: int
    all_complete: bool     # every active assignment is in a terminal status
    all_signed: bool       # all active assignments are concurred or signed
    has_non_concurrence: bool
    lifecycle_step: str    # assign_reviewers | collect_feedback | address_feedback | collect_signatures | complete
    feedback_total: int
    feedback_open: int
    feedback_addressed: int


# ---------------------------------------------------------------------------
# Eligibility check
# ---------------------------------------------------------------------------


def check_concurrence_eligibility(
    project_id: str, assignment_id: str
) -> ConcurrenceEligibility:
    """Return whether a reviewer may concur.

    Rules:
    1. All top-level feedback items from this reviewer must be in a terminal status
       (accepted | rejected | resolved).
    2. For 'question' type items: there must be at least one reply from someone other
       than the reviewer (i.e. the SME has answered).
    """
    from .feedback_ledger import list_feedback_items

    assignment = get_assignment(assignment_id)
    if assignment is None:
        raise KeyError(f"Assignment {assignment_id!r} not found")

    # All feedback from this reviewer on this project
    all_items = list_feedback_items(project_id, reviewer=assignment.reviewer)
    top_level = [i for i in all_items if i.parent_id is None]

    open_items = [i for i in top_level if i.status == "open"]

    # Questions that have no SME reply yet
    unanswered: list[Any] = []
    for q in top_level:
        if q.feedback_type == "question" and q.status == "open":
            replies = list_feedback_items(project_id, parent_id=q.id)  # type: ignore[call-arg]
            has_sme_reply = any(r.reviewer != assignment.reviewer for r in replies)
            if not has_sme_reply:
                unanswered.append(q)

    eligible = len(open_items) == 0 and len(unanswered) == 0

    reason: Optional[str] = None
    if not eligible:
        parts: list[str] = []
        if open_items:
            parts.append(f"{len(open_items)} open feedback item(s) must be addressed first")
        if unanswered:
            parts.append(f"{len(unanswered)} question(s) awaiting SME response")
        reason = "; ".join(parts)

    return ConcurrenceEligibility(
        eligible=eligible,
        open_items=len(open_items),
        unanswered_questions=len(unanswered),
        total_feedback=len(top_level),
        reason=reason,
    )


# ---------------------------------------------------------------------------
# Review summary
# ---------------------------------------------------------------------------


def _compute_lifecycle_step(
    assignments: list[ReviewAssignmentModel],
    feedback_total: int,
    feedback_open: int,
) -> str:
    """Derive the current review lifecycle step from assignment + feedback state."""
    active = [a for a in assignments if a.status != "replaced"]
    if not active:
        return "assign_reviewers"

    terminal_count = sum(1 for a in active if a.status in TERMINAL_STATUSES)
    all_terminal = terminal_count == len(active)

    if all_terminal:
        signed_count = sum(1 for a in active if a.status in ("concurred", "signed"))
        if signed_count == len(active):
            return "complete"
        return "collect_signatures"

    # Any reviewer has submitted feedback or we have feedback items
    if feedback_total > 0 and feedback_open == 0:
        return "collect_signatures"
    if feedback_total > 0:
        return "address_feedback"

    # Reviewers exist but none have submitted yet
    reviewing_count = sum(1 for a in active if a.status in ("reviewing", "feedback_submitted"))
    if reviewing_count > 0:
        return "collect_feedback"

    return "collect_feedback"


def get_review_summary(project_id: str) -> ReviewSummary:
    """Build the full review summary for a project."""
    from .feedback_ledger import get_feedback_progress

    assignments = list_assignments(project_id)
    active = [a for a in assignments if a.status != "replaced"]

    def _cnt(status: str) -> int:
        return sum(1 for a in active if a.status == status)

    terminal_count = sum(1 for a in active if a.status in TERMINAL_STATUSES)
    all_complete = len(active) > 0 and terminal_count == len(active)
    signed_count = _cnt("concurred") + _cnt("signed")
    all_signed = len(active) > 0 and signed_count == len(active)

    try:
        prog = get_feedback_progress(project_id)
        fb_total = prog.total
        fb_open = prog.open
        fb_addressed = prog.addressed
    except Exception:
        fb_total = fb_open = fb_addressed = 0

    step = _compute_lifecycle_step(assignments, fb_total, fb_open)

    return ReviewSummary(
        total_active=len(active),
        invited=_cnt("invited"),
        reviewing=_cnt("reviewing"),
        feedback_submitted=_cnt("feedback_submitted"),
        concurred=_cnt("concurred"),
        non_concurred=_cnt("non_concurred"),
        signed=_cnt("signed"),
        declined=_cnt("declined"),
        all_complete=all_complete,
        all_signed=all_signed,
        has_non_concurrence=_cnt("non_concurred") > 0,
        lifecycle_step=step,
        feedback_total=fb_total,
        feedback_open=fb_open,
        feedback_addressed=fb_addressed,
    )

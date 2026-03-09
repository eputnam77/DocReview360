"""Reviewer assignment, ML scoring, Celery tasks, and run_confirmed_action."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, List

from ..celery_app import app
from ..logs import log_event
from ..ml.onnx_infer import metadata_to_context
from ..quality import approval_likelihood, quality_model_metadata
from ..reviewer_model import ReviewerModel

if TYPE_CHECKING:
    from ..ml.torch_models import TinyCritic

_logger = logging.getLogger(__name__)


def run_confirmed_action(confirm: bool, action: Callable[[], None] | None = None) -> bool:
    """Run ``action`` if ``confirm`` is ``True`` and return the result.

    Returns ``True`` when the action was executed successfully, ``False``
    when ``confirm`` is falsy or the action raises an exception.
    """
    if confirm:
        if action:
            try:
                action()
            except Exception:
                return False
        return True
    return False


def _resolve_pending_approval(event: str, approval_id: str) -> Any:
    from .core import approvals

    approval = approvals.get(approval_id)
    if approval is None:
        log_event(
            f"{event}_skipped",
            severity="warning",
            approval_id=approval_id,
            reason="missing_approval",
        )
        return None
    if approval.state != "pending":
        log_event(
            f"{event}_skipped",
            severity="info",
            approval_id=approval_id,
            reason="approval_not_pending",
            state=approval.state,
            reviewer=approval.reviewer,
            workflow=approval.workflow,
        )
        return None
    return approval


@app.task(name="docreview360.approval_reminder")
def _reminder_task(approval_id: str) -> None:
    """Log a reminder event for ``approval_id``."""
    approval = _resolve_pending_approval("approval_reminder", approval_id)
    if approval is None:
        return
    log_event(
        "approval_reminder",
        approval_id=approval_id,
        reviewer=approval.reviewer,
        workflow=approval.workflow,
        doc_id=approval.document_id,
    )


@app.task(name="docreview360.approval_escalation")
def _escalation_task(approval_id: str, target: str) -> None:
    """Log an escalation event for ``approval_id``."""
    approval = _resolve_pending_approval("approval_escalated", approval_id)
    if approval is None:
        return
    log_event(
        "approval_escalated",
        approval_id=approval_id,
        target=target,
        reviewer=approval.reviewer,
        workflow=approval.workflow,
        doc_id=approval.document_id,
    )


def submit_draft_for_approval(  # noqa: C901
    workflow: str,
    reviewer: str | None,
    doc_id: str,
    text: str,
    critic: "TinyCritic | None",
    *,
    threshold: float = 0.5,
    extra_reviewer: str = "policy",
    reviewer_model: ReviewerModel | None = None,
) -> Any:
    """Score ``text`` and route for additional review if risky."""
    from .core import create_approval

    recommendation = None
    score: float | None = None
    recommendation_payload: List[Dict[str, Any]] = []

    model_summary: dict[str, str] | None = None
    if reviewer_model is not None:
        recommendation = reviewer_model.recommend(text, k=3)
        score = recommendation.approval_likelihood
        recommendation_payload = [
            {"reviewer": name, "probability": probability}
            for name, probability in recommendation.ranked_reviewers
        ]
        model_meta = getattr(reviewer_model, "model_metadata", None)
        model_summary = metadata_to_context(model_meta)
        log_event(
            "reviewer_recommendation",
            workflow=workflow,
            doc_id=doc_id,
            approval_likelihood=score,
            recommendations=recommendation_payload,
            model_version=(model_summary or {}).get("version"),
            model_sha256=(model_summary or {}).get("sha256"),
        )
        if reviewer is None:
            reviewer = recommendation.primary
            if reviewer is None:
                raise ValueError("no reviewer available for draft")
    else:
        if reviewer is None:
            raise ValueError("reviewer_model required when reviewer is None")
        if critic is not None:
            score = approval_likelihood(text, critic)
        model_summary = metadata_to_context(quality_model_metadata())

    scoring_metadata: Dict[str, Any] = {}
    if score is not None:
        scoring_metadata["approval_likelihood"] = score
    if recommendation_payload:
        scoring_metadata["recommendations"] = recommendation_payload
    if model_summary:
        model_payload = {
            key: value
            for key, value in model_summary.items()
            if key in {"sha256", "version", "path"} or key.startswith("docreview360:")
        }
        scoring_metadata["model"] = model_payload
        if "sha256" in model_summary:
            scoring_metadata["model_sha256"] = model_summary["sha256"]
        if "version" in model_summary:
            scoring_metadata["model_version"] = model_summary["version"]

    if score is not None and score < threshold:
        create_approval(
            workflow,
            extra_reviewer,
            doc_id,
            description="Auto risk review",
            scoring_metadata=scoring_metadata.copy(),
        )
    return create_approval(
        workflow,
        reviewer,
        doc_id,
        description="Primary review",
        scoring_metadata=scoring_metadata.copy(),
    )

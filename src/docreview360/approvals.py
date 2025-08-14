"""Approval management with digital signature placeholder."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict

from .logs import log_event
from .workflows import workflows
from .integrations.signature import get_provider, DEFAULT_PROVIDER
from .quality import approval_likelihood
from .fann_model import Weights


class ApprovalModel(BaseModel):
    """Representation of an approval record."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    workflow: str
    reviewer: str
    state: str = "pending"
    due_at: datetime | None = None
    signature_provider: str = DEFAULT_PROVIDER
    signature_id: Optional[str] = Field(default=None, alias="signature")
    document_hash: Optional[str] = None
    certificate_url: Optional[str] = None
    signed_at: datetime | None = None
    description: Optional[str] = None  # Description from the approval step


approvals: Dict[str, ApprovalModel] = {}


def create_approval(
    workflow: str,
    reviewer: str,
    due_at: datetime | None = None,
    description: str | None = None,
    *,
    signature_provider: str = DEFAULT_PROVIDER,
    document: bytes | None = None,
) -> ApprovalModel:
    """Create a pending approval for the given workflow and reviewer."""
    approval_id = uuid4().hex
    doc_hash = hashlib.sha256(document).hexdigest() if document else None
    approval = ApprovalModel(
        id=approval_id,
        workflow=workflow,
        reviewer=reviewer,
        due_at=due_at,
        description=description,
        signature_provider=signature_provider,
        document_hash=doc_hash,
    )
    approvals[approval_id] = approval
    log_event(
        "approval_created",
        user=reviewer,
        workflow=workflow,
        approval_id=approval_id,
        provider=signature_provider,
        document_hash=doc_hash,
    )
    return approval


def get_approval(approval_id: str) -> ApprovalModel | None:
    """Retrieve a single approval by id."""
    return approvals.get(approval_id)


def list_approvals(workflow: str | None = None) -> List[ApprovalModel]:
    """Return approvals, optionally filtered by workflow id."""
    if workflow is None:
        return list(approvals.values())
    return [a for a in approvals.values() if a.workflow == workflow]


def submit_draft_for_approval(
    workflow: str,
    reviewer: str,
    text: str,
    weights: Weights,
    *,
    threshold: float = 0.5,
    extra_reviewer: str = "policy",
) -> ApprovalModel:
    """Score ``text`` and route for additional review if risky.

    Drafts with an approval likelihood below ``threshold`` are first sent to
    ``extra_reviewer`` before the main ``reviewer`` receives the approval
    request.  This connects FANN scoring with the workflow system for
    proactive risk mitigation.
    """

    score = approval_likelihood(text, weights)
    if score < threshold:
        create_approval(workflow, extra_reviewer, description="Auto risk review")
    return create_approval(workflow, reviewer, description="Primary review")


def update_approval_state(
    approval_id: str,
    state: str,
    signature_id: str | None = None,
    *,
    certificate_url: str | None = None,
    signed_at: datetime | None = None,
    due_at: datetime | None = None,
) -> ApprovalModel:
    """Set approval state and optional digital signature metadata."""
    approval = approvals[approval_id]
    previous = approval.state
    approval.state = state
    if signature_id is not None:
        approval.signature_id = signature_id
    if certificate_url is not None:
        approval.certificate_url = certificate_url
    if due_at is not None:
        approval.due_at = due_at
    if state == "approved":
        approval.signed_at = signed_at or datetime.now(timezone.utc)
    else:
        approval.signed_at = None
        approval.certificate_url = None
    wf = workflows.get(approval.workflow)
    project_id = wf.project if wf else ""
    log_event(
        f"approval_{state}",
        user=approval.reviewer,
        project=project_id,
        approval_id=approval_id,
        provider=approval.signature_provider,
        signature_id=approval.signature_id,
        document_hash=approval.document_hash,
        previous_state=previous,
    )
    if state == "approved" and wf:
        # check if all approvals done
        if all(
            a.state == "approved" and a.workflow == approval.workflow
            for a in approvals.values()
            if a.workflow == approval.workflow
        ):
            log_event(
                f"All required approvals completed for project {project_id}",
                project=project_id,
            )
    return approval


def send_for_signature(
    approval_id: str,
    document_id: str,
    user: str,
    return_url: str | None = None,
) -> str:
    """Trigger the active provider to request a signature for this approval.

    Returns the provider signing URL.
    """

    approval = approvals[approval_id]
    provider = get_provider(approval.signature_provider)
    sig_id, url = provider.request_signature(
        document_id,
        user,
        workflow_id=approval.workflow,
        approval_id=approval_id,
        return_url=return_url,
    )
    approval.signature_id = sig_id
    log_event(
        "approval_sent_for_signature",
        user=user,
        approval_id=approval_id,
        provider=approval.signature_provider,
        signature_id=sig_id,
        workflow=approval.workflow,
    )
    return url


def verify_document_hash(approval_id: str, document: bytes) -> bool:
    """Validate ``document`` matches the stored hash for ``approval_id``."""

    approval = approvals[approval_id]
    if approval.document_hash is None:
        return True
    return approval.document_hash == hashlib.sha256(document).hexdigest()


def reset_approval(approval_id: str, confirm: bool) -> bool:
    """Reset the state of an approval to ``pending`` if confirmed."""

    from .stubs.task213 import task213

    def _do_reset() -> None:
        approval = approvals.get(approval_id)
        if approval is None:
            raise KeyError("approval not found")
        previous = approval.state
        approval.state = "pending"
        approval.signature_id = None
        approval.signed_at = None
        log_event(
            "approval_reset",
            user=approval.reviewer,
            approval_id=approval_id,
            provider=approval.signature_provider,
            previous_state=previous,
        )

    return task213(confirm, _do_reset)

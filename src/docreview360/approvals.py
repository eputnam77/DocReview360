"""Approval management with digital signature placeholder."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel

from .logs import log_event
from .workflows import workflows


class ApprovalModel(BaseModel):
    """Representation of an approval record."""

    id: str
    workflow: str
    reviewer: str
    state: str = "pending"
    due_at: datetime | None = None
    signature: Optional[str] = None
    signed_at: Optional[str] = None


approvals: Dict[str, ApprovalModel] = {}


def create_approval(workflow: str, reviewer: str, due_at: datetime | None = None) -> ApprovalModel:
    """Create a pending approval for the given workflow and reviewer."""
    approval_id = uuid4().hex
    approval = ApprovalModel(id=approval_id, workflow=workflow, reviewer=reviewer, due_at=due_at)
    approvals[approval_id] = approval
    return approval


def get_approval(approval_id: str) -> ApprovalModel | None:
    """Retrieve a single approval by id."""
    return approvals.get(approval_id)


def list_approvals(workflow: str | None = None) -> List[ApprovalModel]:
    """Return approvals, optionally filtered by workflow id."""
    if workflow is None:
        return list(approvals.values())
    return [a for a in approvals.values() if a.workflow == workflow]


def update_approval_state(
    approval_id: str,
    state: str,
    signature: str | None = None,
    *,
    due_at: datetime | None = None,
) -> ApprovalModel:
    """Set approval state and optional digital signature placeholder."""
    approval = approvals[approval_id]
    approval.state = state
    approval.signature = signature
    if due_at is not None:
        approval.due_at = due_at
    if state == "approved":
        approval.signed_at = datetime.now(timezone.utc).isoformat()
    else:
        approval.signed_at = None
    if state == "approved":
        wf = workflows.get(approval.workflow)
        project_id = wf.project if wf else ""
        log_event(
            f"{approval.reviewer} approved document {project_id} with digital signature",
            user=approval.reviewer,
            project=project_id,
        )
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


def reset_approval(approval_id: str, confirm: bool) -> bool:
    """Reset the state of an approval to ``pending`` if confirmed."""

    from .stubs.task213 import task213

    def _do_reset() -> None:
        approval = approvals.get(approval_id)
        if approval is None:
            raise KeyError("approval not found")
        approval.state = "pending"
        approval.signature = None
        approval.signed_at = None

    return task213(confirm, _do_reset)

"""Approval management with digital signature placeholder."""

from __future__ import annotations

from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel


class ApprovalModel(BaseModel):
    """Representation of an approval record."""

    id: str
    workflow: str
    reviewer: str
    state: str = "pending"
    signature: Optional[str] = None


approvals: Dict[str, ApprovalModel] = {}


def create_approval(workflow: str, reviewer: str) -> ApprovalModel:
    """Create a pending approval for the given workflow and reviewer."""
    approval_id = uuid4().hex
    approval = ApprovalModel(id=approval_id, workflow=workflow, reviewer=reviewer)
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
    approval_id: str, state: str, signature: str | None = None
) -> ApprovalModel:
    """Set approval state and optional digital signature placeholder."""
    approval = approvals[approval_id]
    approval.state = state
    approval.signature = signature
    return approval

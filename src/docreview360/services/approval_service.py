# SPDX-License-Identifier: MIT
"""Approval service — business logic wrapper around approval CRUD operations."""

from __future__ import annotations

import logging
from typing import Optional

from ..approvals.core import ApprovalModel

_logger = logging.getLogger(__name__)


class ApprovalService:
    """Thin service layer for approval lifecycle operations.

    Centralises approval business logic so that routers stay thin and the
    domain rules are independently testable.
    """

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get(self, approval_id: str) -> Optional[ApprovalModel]:
        """Return an approval by ID or ``None`` if it does not exist."""
        from ..approvals import get_approval

        return get_approval(approval_id)

    def list(
        self,
        workflow: Optional[str] = None,
        phase_id: Optional[str] = None,
    ) -> list[ApprovalModel]:
        """Return approvals, optionally filtered by workflow and/or phase."""
        from ..approvals import list_approvals

        return list_approvals(workflow=workflow, phase_id=phase_id)

    def get_by_signature(self, signature_id: str) -> Optional[ApprovalModel]:
        """Look up an approval by its signature provider reference ID."""
        from ..approvals.core import get_approval_by_signature

        return get_approval_by_signature(signature_id)

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def create(self, **kwargs: object) -> ApprovalModel:
        """Create and persist a new approval record."""
        from ..approvals import create_approval

        approval = create_approval(**kwargs)  # type: ignore[arg-type]
        _logger.info("Created approval %s for workflow %s", approval.id, approval.workflow)
        return approval

    def update_state(self, approval_id: str, state: str, **meta: object) -> ApprovalModel:
        """Transition an approval to a new state."""
        from ..approvals import update_approval_state

        _logger.info("Transitioning approval %s to state %r", approval_id, state)
        return update_approval_state(approval_id, state, **meta)  # type: ignore[arg-type]

    def delete(self, approval_id: str) -> None:
        """Remove an approval record."""
        from ..approvals import delete_approval

        _logger.info("Deleting approval %s", approval_id)
        delete_approval(approval_id)

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def assert_exists(self, approval_id: str) -> ApprovalModel:
        """Return the approval or raise ``KeyError`` if it does not exist."""
        approval = self.get(approval_id)
        if approval is None:
            raise KeyError(f"Approval not found: {approval_id}")
        return approval

    def is_terminal(self, approval: ApprovalModel) -> bool:
        """Return ``True`` when the approval is in a terminal state."""
        return approval.state in {"approved", "rejected", "signed"}

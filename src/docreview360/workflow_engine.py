"""Lightweight workflow engine for approval step progression."""

from __future__ import annotations

from typing import List

from .approvals import ApprovalModel, approvals


class WorkflowEngine:
    """Determine active approval steps for workflows."""

    def active_approvals(self, wf_id: str) -> List[ApprovalModel]:
        # Determine active approvals without depending on the workflow registry.
        # This avoids KeyError when the workflow mapping has been cleared in
        # tests while approvals still capture the progression semantics.
        steps = [a for a in approvals.values() if a.workflow == wf_id]
        if not steps:
            return []

        # Heuristic: in sequential mode, non-current steps are marked "future".
        # In parallel mode all non-approved steps are actionable ("pending").
        is_sequential = any(a.state == "future" for a in steps)
        if not is_sequential:
            return [a for a in steps if a.state != "approved"]

        ordered = sorted(steps, key=lambda a: a.order)
        for step in ordered:
            if step.state != "approved":
                return [step]
        return []


engine = WorkflowEngine()

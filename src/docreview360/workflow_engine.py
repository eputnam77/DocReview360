"""Lightweight workflow engine for approval step progression."""

from __future__ import annotations

from typing import List

from .approvals import ApprovalModel, approvals
from .workflows import WorkflowModel, workflows


class WorkflowEngine:
    """Determine active approval steps for workflows."""

    def active_approvals(self, wf_id: str) -> List[ApprovalModel]:
        wf: WorkflowModel = workflows[wf_id]
        steps = [a for a in approvals.values() if a.workflow == wf_id]
        if wf.mode == "parallel":
            return [a for a in steps if a.state != "approved"]
        ordered = sorted(steps, key=lambda a: a.order)
        for step in ordered:
            if step.state != "approved":
                return [step]
        return []


engine = WorkflowEngine()

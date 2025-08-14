"""Workflow cloning utilities (Task 144)."""

from __future__ import annotations

from typing import Iterable
from uuid import uuid4

from .stubs import record_task_completion
from .workflows import WorkflowModel, workflows


def clone_workflow(wf_id: str, reviewers: Iterable[str] | None = None) -> WorkflowModel:
    """Return a copy of ``wf_id`` with optional ``reviewers`` override."""
    original = workflows.get(wf_id)
    if original is None:
        raise KeyError(f"workflow {wf_id} not found")
    clone = WorkflowModel(
        id=uuid4().hex,
        project=original.project,
        phase=original.phase,
        phases=list(original.phases),
        reviewers=list(reviewers or original.reviewers),
        template=original.template,
        approval_steps=[s.model_copy() for s in original.approval_steps],
    )
    workflows[clone.id] = clone
    record_task_completion(144)
    return clone

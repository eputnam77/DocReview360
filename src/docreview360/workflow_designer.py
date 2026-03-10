# SPDX-License-Identifier: MIT
"""Workflow cloning utilities (Task 144)."""

from __future__ import annotations

from typing import Iterable
from uuid import uuid4

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
        reviewers=list(original.reviewers if reviewers is None else reviewers),
        template=original.template,
        # ``ApprovalStep`` instances may originate from an older import of the
        # ``workflows`` module.  Serialising each step ensures Pydantic rebuilds
        # them using the current model class, avoiding cross-module validation
        # errors.
        approval_steps=[s.model_dump() for s in original.approval_steps],
    )
    workflows[clone.id] = clone
    return clone

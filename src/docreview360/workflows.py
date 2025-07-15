from __future__ import annotations

from typing import Callable, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel


class WorkflowModel(BaseModel):
    """Simple workflow representation."""

    id: str
    project: str
    phase: str
    phases: List[str]
    reviewers: List[str] = []
    document: Optional[str] = None


workflows: Dict[str, WorkflowModel] = {}

# Registered callbacks mimicking agileagents bot webhooks
bot_callbacks: list[Callable[[WorkflowModel], None]] = []


def register_bot(callback: Callable[[WorkflowModel], None]) -> None:
    """Register an automation bot callback."""
    bot_callbacks.append(callback)


def create_workflow(project: str, phases: List[str]) -> WorkflowModel:
    """Create a workflow for a project starting at the first phase."""
    wf_id = uuid4().hex
    start_phase = phases[0] if phases else "start"
    workflow = WorkflowModel(id=wf_id, project=project, phase=start_phase, phases=phases)
    workflows[wf_id] = workflow
    for cb in bot_callbacks:
        cb(workflow)
    return workflow


def get_workflow(wf_id: str) -> WorkflowModel | None:
    """Return a workflow by id."""
    return workflows.get(wf_id)


def assign_reviewer(wf_id: str, user: str) -> WorkflowModel:
    """Assign a reviewer to the workflow."""
    workflow = workflows[wf_id]
    if user not in workflow.reviewers:
        workflow.reviewers.append(user)
    return workflow


def advance_workflow(wf_id: str) -> WorkflowModel:
    """Move the workflow to the next phase."""
    workflow = workflows[wf_id]
    try:
        idx = workflow.phases.index(workflow.phase)
    except ValueError as exc:  # pragma: no cover - invalid phase is unreachable in tests
        raise KeyError(f"Unknown phase '{workflow.phase}'") from exc
    if idx + 1 >= len(workflow.phases):
        workflow.phase = workflow.phases[-1]
    else:
        workflow.phase = workflow.phases[idx + 1]
    for cb in bot_callbacks:
        cb(workflow)
    return workflow


def start_workflow(wf_id: str, title: str, data: bytes | None = None) -> WorkflowModel:
    """Attach a document to the workflow and mark it as started."""

    from .documents import import_document

    workflow = workflows[wf_id]
    filename = title if title.endswith((".md", ".doc", ".docx")) else f"{title}.md"
    content = data or b"-"
    document = import_document(filename, content, project=workflow.project)
    workflow.document = document.id
    if workflow.phases:
        workflow.phase = workflow.phases[0]
    return workflow

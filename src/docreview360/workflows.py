"""Simplified workflow tracking models."""

from __future__ import annotations

from typing import Callable, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel


class ApprovalStep(BaseModel):
    """Represents an approval step in a workflow."""

    role: str
    description: str
    order: int
    required: bool = True


class WorkflowModel(BaseModel):
    """Simple workflow representation."""

    id: str
    project: str
    phase: str
    phases: List[str]
    reviewers: List[str] = []
    document: Optional[str] = None
    template: str = "branch-coordination"
    approval_steps: List[ApprovalStep] = []
    # distinct roles participating in approvals
    approval_roles: List[str] = []
    # sequence of roles in the order they must approve
    approval_sequence: List[str] = []


workflows: Dict[str, WorkflowModel] = {}

# Registered callbacks mimicking agileagents bot webhooks
bot_callbacks: list[Callable[[WorkflowModel], None]] = []

# Workflow templates keyed by name
workflow_templates: Dict[str, List[ApprovalStep]] = {
    "branch-coordination": [
        ApprovalStep(
            role="SME",
            description="Subject Matter Expert review and validation",
            order=1,
        ),
        ApprovalStep(
            role="Front Line Manager",
            description="Front Line Manager approval",
            order=2,
        ),
        ApprovalStep(
            role="Product Policy Manager",
            description="Product Policy Manager review and approval",
            order=3,
        ),
        ApprovalStep(
            role="Technical Writer",
            description="Technical Writer review and editing",
            order=4,
        ),
        ApprovalStep(
            role="Senior Technical Writer",
            description="Senior Technical Writer review and approval",
            order=5,
        ),
        ApprovalStep(
            role="Technical Writing Manager",
            description="Technical Writing Manager final approval",
            order=6,
        ),
    ],
    "pre-coordination": [
        ApprovalStep(
            role="Writer",
            description="Initial drafting and self-check",
            order=1,
        ),
        ApprovalStep(
            role="Peer Reviewer",
            description="Peer review for technical soundness",
            order=2,
        ),
        ApprovalStep(
            role="Branch Liaison",
            description="Confirms alignment with branch priorities",
            order=3,
        ),
    ],
    "requirements-data-gathering": [
        ApprovalStep(
            role="Research Analyst",
            description="Collects background data and stakeholder requirements",
            order=1,
        ),
        ApprovalStep(
            role="Legal/Regulatory Reviewer",
            description="Identifies statutory constraints",
            order=2,
        ),
        ApprovalStep(
            role="Writer",
            description="Creates annotated outline for downstream reviewers",
            order=3,
        ),
    ],
    "fast-track-coordination": [
        ApprovalStep(
            role="Writer",
            description="Drafts minor or urgent changes",
            order=1,
        ),
        ApprovalStep(
            role="SME",
            description="Subject Matter Expert review",
            order=2,
        ),
        ApprovalStep(
            role="Senior Technical Writer",
            description="Final review and approval",
            order=3,
        ),
    ],
    "multi-branch-coordination": [
        ApprovalStep(
            role="SME (Branch A)",
            description="Branch A SME review",
            order=1,
        ),
        ApprovalStep(
            role="SME (Branch B)",
            description="Branch B SME review",
            order=2,
        ),
        ApprovalStep(
            role="Branch Managers (A and B)",
            description="Management approval from both branches",
            order=3,
        ),
        ApprovalStep(
            role="Senior Technical Writer",
            description="Senior Technical Writer review",
            order=4,
        ),
        ApprovalStep(
            role="Technical Writing Manager",
            description="Technical Writing Manager final approval",
            order=5,
        ),
    ],
    "external-partner-coordination": [
        ApprovalStep(
            role="Internal SME",
            description="Internal subject matter expert review",
            order=1,
        ),
        ApprovalStep(
            role="Public Affairs",
            description="Communications and public affairs review",
            order=2,
        ),
        ApprovalStep(
            role="External Stakeholder",
            description="External stakeholder review",
            order=3,
        ),
        ApprovalStep(
            role="Technical Writer",
            description="Incorporates external feedback",
            order=4,
        ),
        ApprovalStep(
            role="Technical Writing Manager",
            description="Final internal approval",
            order=5,
        ),
    ],
    "publication-distribution": [
        ApprovalStep(
            role="Technical Writer",
            description="Prepares publication version",
            order=1,
        ),
        ApprovalStep(
            role="Communications/Outreach",
            description="Distributes to official channels",
            order=2,
        ),
        ApprovalStep(
            role="Records Management",
            description="Archives final version in CMS",
            order=3,
        ),
    ],
    "implementation-tracking": [
        ApprovalStep(
            role="Program Manager",
            description="Notifies affected teams",
            order=1,
        ),
        ApprovalStep(
            role="Compliance Officer",
            description="Confirms procedures updated",
            order=2,
        ),
        ApprovalStep(
            role="Records Management",
            description="Archive and close workflow",
            order=3,
        ),
    ],
}


def get_approval_steps_for_phase(
    phase: str, workflow: str = "branch-coordination"
) -> List[ApprovalStep]:
    """Return approval steps for the given workflow."""
    try:
        steps = workflow_templates[workflow]
    except KeyError as exc:
        raise KeyError(f"Unknown workflow '{workflow}'") from exc
    return [step.model_copy() for step in steps]


def _bootstrap_sample() -> None:
    """Create a default workflow so the API returns initial data."""
    if workflows:
        return

    from .phases import list_phases

    phases = list_phases()
    start_phase = phases[0] if phases else "start"
    for name in workflow_templates:
        steps = get_approval_steps_for_phase(start_phase, name)
        workflows[name] = WorkflowModel(
            id=name,
            project=name,
            phase=start_phase,
            phases=phases or [start_phase],
            template=name,
            approval_steps=steps,
            approval_roles=[s.role for s in steps],
            approval_sequence=[s.role for s in sorted(steps, key=lambda s: s.order)],
        )


_bootstrap_sample()


def register_bot(callback: Callable[[WorkflowModel], None]) -> None:
    """Register an automation bot callback."""
    bot_callbacks.append(callback)


def create_workflow(
    project: str, phases: List[str], template: str = "branch-coordination"
) -> WorkflowModel:
    """Create a workflow for a project starting at the first phase."""
    wf_id = uuid4().hex
    start_phase = phases[0] if phases else "start"

    # Generate approval steps based on the selected template
    approval_steps = get_approval_steps_for_phase(start_phase, template)
    approval_roles = [s.role for s in approval_steps]
    approval_sequence = [s.role for s in sorted(approval_steps, key=lambda s: s.order)]

    workflow = WorkflowModel(
        id=wf_id,
        project=project,
        phase=start_phase,
        phases=phases,
        template=template,
        approval_steps=approval_steps,
        approval_roles=approval_roles,
        approval_sequence=approval_sequence,
    )
    workflows[wf_id] = workflow

    # Create initial approval entries for each step
    from .approvals import create_approval

    for step in approval_steps:
        create_approval(wf_id, step.role, wf_id, due_at=None, description=step.description)

    for cb in bot_callbacks:
        cb(workflow)
    return workflow


def get_workflow(wf_id: str) -> WorkflowModel | None:
    """Return a workflow by id."""
    return workflows.get(wf_id)


def list_workflows(project: str | None = None) -> list[WorkflowModel]:
    """Return workflows optionally filtered by project."""
    if project is None:
        return list(workflows.values())
    return [wf for wf in workflows.values() if wf.project == project]


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
    except ValueError as exc:
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

    from .approvals import approvals as approval_store
    from .audit import log_audit_event
    from .documents import import_document, link_approval, unlink_approval
    from .logs import log_event

    workflow = workflows[wf_id]
    filename = title if title.endswith((".md", ".doc", ".docx")) else f"{title}.md"
    content = data or b"-"
    document = import_document(filename, content, project=workflow.project)
    workflow.document = document.id

    # Ensure all existing approvals reference the newly attached document so
    # subsequent history logs retain the correct source linkage.
    for approval in approval_store.values():
        if approval.workflow == wf_id:
            if approval.document_id != document.id:
                unlink_approval(approval.document_id, approval.id)
                approval.document_id = document.id
                link_approval(document.id, approval.id)
                log_event(
                    "approval_doc_linked",
                    approval_id=approval.id,
                    workflow=wf_id,
                    doc_id=document.id,
                )
                log_audit_event(
                    document.id,
                    "approval_doc_linked",
                    approval_id=approval.id,
                    workflow=wf_id,
                )

    if workflow.phases:
        workflow.phase = workflow.phases[0]
    return workflow

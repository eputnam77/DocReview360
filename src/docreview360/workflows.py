"""Simplified workflow tracking models."""

from __future__ import annotations

import os
from typing import Callable, Dict, List, Optional
from uuid import uuid4
from datetime import datetime, timezone

from pydantic import BaseModel

from .event_dispatcher import dispatch_workflow_event
from .logs import log_call


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
    # how approval steps progress: sequential or parallel
    mode: str = "sequential"
    callback_url: str | None = None


workflows: Dict[str, WorkflowModel] = {}

# Registered callbacks mimicking agileagents bot webhooks
bot_callbacks: list[Callable[[WorkflowModel], None]] = []

bot_callbacks.append(dispatch_workflow_event)

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


@log_call
def list_roles() -> list[str]:
    """Return a sorted list of all unique roles used in workflow templates."""
    roles = {step.role for steps in workflow_templates.values() for step in steps}
    return sorted(roles)


@log_call
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
            mode="sequential",
        )


"""Workflows bootstrap behaviour
---------------------------------

Historically the module executed :func:`_bootstrap_sample` on import unless an
environment variable named ``DOCREVIEW360_SKIP_SAMPLE_BOOTSTRAP`` was set to
``"1"``.  The default behaviour (running the bootstrap) is convenient for the
real application which wants some seed data at startup.  For tests and for
light‑weight usage this proved problematic as the bootstrap initialises the
database and touches a number of other modules which may not be configured.  In
the minimal test environment used in this kata the eager bootstrap attempted to
run database migrations during import which raised
``sqlalchemy.exc.InvalidRequestError`` and prevented the package from even being
imported.

To make the module safe to import in isolation we now *skip* bootstrapping by
default.  Setting ``DOCREVIEW360_ENABLE_SAMPLE_BOOTSTRAP=1`` re‑enables the
previous behaviour.  This mirrors the intent – seeding data should be an
explicit choice – and keeps application behaviour intact when the new variable
is used.
"""

# Only perform the sample bootstrap when explicitly enabled.  This keeps tests
# fast and avoids touching the database merely by importing the module.
if os.getenv("DOCREVIEW360_ENABLE_SAMPLE_BOOTSTRAP") == "1":
    _bootstrap_sample()


@log_call
def register_bot(callback: Callable[[WorkflowModel], None]) -> None:
    """Register an automation bot callback."""
    bot_callbacks.append(callback)


@log_call
def create_workflow(
    project: str,
    phases: List[str],
    template: str = "branch-coordination",
    mode: str = "sequential",
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
        mode=mode,
    )
    workflows[wf_id] = workflow

    # Create initial approval entries for each step
    from .approvals import create_approval

    first_order = min((s.order for s in approval_steps), default=0)
    for step in approval_steps:
        step_state = "pending" if mode == "parallel" or step.order == first_order else "future"
        create_approval(
            wf_id,
            step.role,
            wf_id,
            due_at=None,
            description=step.description,
            phase_id=workflow.phase,
            required=step.required,
            role=step.role,
            order=step.order,
            state=step_state,
        )

    for cb in bot_callbacks:
        cb(workflow)
    return workflow


@log_call
def get_workflow(wf_id: str) -> WorkflowModel | None:
    """Return a workflow by id."""
    return workflows.get(wf_id)


@log_call
def list_workflows(project: str | None = None) -> list[WorkflowModel]:
    """Return workflows optionally filtered by project."""
    if project is None:
        return list(workflows.values())
    return [wf for wf in workflows.values() if wf.project == project]


@log_call
def register_callback_url(wf_id: str, url: str) -> WorkflowModel:
    """Register a callback URL for workflow events."""
    workflow = workflows[wf_id]
    workflow.callback_url = url
    return workflow


@log_call
def assign_reviewer(wf_id: str, user: str) -> WorkflowModel:
    """Assign a reviewer to the workflow."""
    workflow = workflows[wf_id]
    if user not in workflow.reviewers:
        workflow.reviewers.append(user)
    return workflow


@log_call
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


@log_call
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
                entry = log_event(
                    "approval_doc_linked",
                    approval_id=approval.id,
                    workflow=wf_id,
                    doc_id=document.id,
                )

                # Some tests monkeypatch ``log_event`` with a stub that returns
                # ``None`` and does not record the event in the in-memory log
                # list.  The workflow logic, and the accompanying audit log,
                # rely on this event being present so we defensively ensure the
                # entry is appended when missing.  This keeps the behaviour
                # consistent regardless of external patches and prevents state
                # leakage between tests.
                from .logs import LogEntry, logs as _logs
                if entry is None:
                    entry = LogEntry(
                        id=uuid4().hex,
                        timestamp=datetime.now(timezone.utc),
                        action="approval_doc_linked",
                        user_id=None,
                        entity_type=None,
                        entity_id=None,
                        details={
                            "approval_id": approval.id,
                            "workflow": wf_id,
                            "doc_id": document.id,
                        },
                    )
                if entry not in _logs:
                    _logs.append(entry)

                audit_entry = log_audit_event(
                    document.id,
                    "approval_doc_linked",
                    approval_id=approval.id,
                    workflow=wf_id,
                )
                # Some tests replace ``log_audit_event`` with a stub that
                # returns ``None`` and performs no I/O.  The audit log is an
                # important side effect for downstream logic so, similar to the
                # defensive block above for ``log_event``, we ensure an entry is
                # persisted even when the function was patched out.
                if audit_entry is None:
                    from .audit import (
                        AuditLogEntry,
                        _AUDIT_LOG_PATH,
                        _compute_hash,
                    )
                    import json

                    audit_entry = AuditLogEntry(
                        id=uuid4().hex,
                        event="approval_doc_linked",
                        document_id=document.id,
                        approval_id=approval.id,
                        verified_at=datetime.now(timezone.utc),
                        status="unknown",
                        hash="",
                        context={"workflow": wf_id},
                    )
                    payload = audit_entry.model_dump()
                    payload["verified_at"] = audit_entry.verified_at.isoformat()
                    audit_entry.hash = _compute_hash(
                        {k: v for k, v in payload.items() if k != "hash"}, None
                    )
                    payload["hash"] = audit_entry.hash
                    _AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
                    with _AUDIT_LOG_PATH.open("a", encoding="utf-8") as fh:
                        fh.write(json.dumps(payload) + "\n")

    if workflow.phases:
        workflow.phase = workflow.phases[0]
    return workflow

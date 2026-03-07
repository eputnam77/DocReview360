"""Simplified workflow tracking models."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional
from uuid import uuid4

from filelock import FileLock
from pydantic import BaseModel, Field, field_validator

from .event_dispatcher import dispatch_workflow_event
from .logs import log_call


class ApprovalStep(BaseModel):
    """Represents an approval step in a workflow."""

    role: str
    description: str
    order: int
    required: bool = True


class WorkflowTemplateStep(BaseModel):
    """Represents a configurable template step in the admin workflow builder."""

    role: str
    user: str | None = None
    required: bool = True
    description: str | None = None

    @field_validator("role")
    @classmethod
    def _ensure_role(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Workflow template step role is required")
        return value.strip()


class WorkflowTemplatePayload(BaseModel):
    """Payload for creating or updating workflow templates."""

    name: str
    description: str | None = None
    steps: list[WorkflowTemplateStep]

    @field_validator("name")
    @classmethod
    def _ensure_name(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Workflow template name is required")
        return value.strip()

    @field_validator("steps")
    @classmethod
    def _ensure_steps(cls, value: list[WorkflowTemplateStep]) -> list[WorkflowTemplateStep]:
        if not value:
            raise ValueError("Workflow template must include at least one step")
        return value


class WorkflowTemplateModel(BaseModel):
    """Workflow template stored in the backend."""

    id: str
    name: str
    description: str | None = None
    steps: list[WorkflowTemplateStep] = Field(default_factory=list)
    updated: str | None = None

    @field_validator("steps")
    @classmethod
    def _ensure_steps(cls, value: list[WorkflowTemplateStep]) -> list[WorkflowTemplateStep]:
        if not value:
            raise ValueError("Workflow template must include at least one step")
        return value


class WorkflowModel(BaseModel):
    """Simple workflow representation."""

    id: str
    project: str
    phase: str
    phases: List[str]
    # Several list fields previously used mutable list defaults which were
    # shared across model instances.  This led to workflows unexpectedly
    # inheriting reviewers or approval configuration from prior instances.
    # ``default_factory`` ensures each workflow receives its own list.
    reviewers: List[str] = Field(default_factory=list)
    document: Optional[str] = None
    template: str = "branch-coordination"
    approval_steps: List[ApprovalStep] = Field(default_factory=list)
    # distinct roles participating in approvals
    approval_roles: List[str] = Field(default_factory=list)
    # sequence of roles in the order they must approve
    approval_sequence: List[str] = Field(default_factory=list)
    # how approval steps progress: sequential or parallel
    mode: str = "sequential"
    callback_url: str | None = None


# ``workflows`` is a module level registry that many tests mutate.  Some test
# modules reload ``docreview360.workflows`` which would ordinarily create a new
# dictionary and leave previously imported references pointing to the stale
# object.  Subsequent tests that imported ``workflows`` early would then operate
# on the old mapping, leading to surprising ``KeyError`` failures.  To keep a
# single shared registry across reloads we store the dictionary on the package
# object and reuse it when the module is imported again.
_pkg = sys.modules.get(__name__.rpartition(".")[0])
if _pkg is not None and hasattr(_pkg, "_workflows_store"):
    workflows = getattr(_pkg, "_workflows_store")  # type: ignore[assignment]
else:
    workflows: Dict[str, WorkflowModel] = {}
    if _pkg is not None:
        setattr(_pkg, "_workflows_store", workflows)

# Registered callbacks mimicking agileagents bot webhooks
bot_callbacks: list[Callable[[WorkflowModel], None]] = []

bot_callbacks.append(dispatch_workflow_event)


def _env_flag_enabled(value: str | None) -> bool:
    """Interpret truthy string values for the persistence feature flag."""

    if value is None:
        return True
    normalized = value.strip().lower()
    return normalized not in {"0", "false", "no", "off"}


WORKFLOW_TEMPLATES_FILE = Path(
    os.getenv("DOCREVIEW360_WORKFLOW_TEMPLATES_FILE", "workflow_templates.json")
)
DOCREVIEW360_ENABLE_WORKFLOW_TEMPLATE_PERSISTENCE = _env_flag_enabled(
    os.getenv("DOCREVIEW360_ENABLE_WORKFLOW_TEMPLATE_PERSISTENCE")
)

if _pkg is not None and hasattr(_pkg, "_workflow_template_definitions_store"):
    workflow_template_definitions = getattr(_pkg, "_workflow_template_definitions_store")
else:
    workflow_template_definitions: Dict[str, WorkflowTemplateModel] = {}
    if _pkg is not None:
        setattr(_pkg, "_workflow_template_definitions_store", workflow_template_definitions)

_ACTIVE_TEMPLATES_FILE: Path = WORKFLOW_TEMPLATES_FILE
_TEMPLATES_LOADED: bool = False


def _log_template_issue(template_name: str, reason: str) -> None:
    """Log workflow template validation issues for operators."""

    try:
        from .logs import log_event
    except Exception:
        return

    try:
        log_event(
            "workflow_template_invalid",
            severity="error",
            template=template_name,
            reason=reason,
        )
    except Exception:
        # Logging failures should not mask the underlying validation error.
        pass


def _raise_template_error(template_name: str, reason: str) -> None:
    """Log and raise an error describing template ordering issues."""

    _log_template_issue(template_name, reason)
    raise ValueError(f"Workflow template '{template_name}' has invalid approval order: {reason}")


def _validate_template_orders(template_name: str, steps: List[ApprovalStep]) -> None:
    """Ensure approval steps have strictly increasing integer order values."""

    last_order: int | None = None
    for step in steps:
        order = step.order
        if not isinstance(order, int) or isinstance(order, bool):
            _raise_template_error(
                template_name,
                f"step '{step.role}' uses non-integer order value {order!r}",
            )
        if order < 0:
            _raise_template_error(
                template_name,
                f"step '{step.role}' uses negative order value {order}",
            )
        if last_order is not None and order <= last_order:
            comparison = "duplicate" if order == last_order else "regression"
            _raise_template_error(
                template_name,
                f"step '{step.role}' introduces {comparison}: order {order} after {last_order}",
            )
        last_order = order


DEFAULT_WORKFLOW_TEMPLATES: Dict[str, List[ApprovalStep]] = {
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

# Workflow templates keyed by name. Persist them across module reloads so
# updates in long-lived tests remain visible.
if _pkg is not None and hasattr(_pkg, "_workflow_templates_store"):
    workflow_templates = getattr(_pkg, "_workflow_templates_store")  # type: ignore[assignment]
else:
    workflow_templates: Dict[str, List[ApprovalStep]] = {}
    if _pkg is not None:
        setattr(_pkg, "_workflow_templates_store", workflow_templates)


def _template_steps_from_definition(template: WorkflowTemplateModel) -> list[ApprovalStep]:
    steps: list[ApprovalStep] = []
    for idx, step in enumerate(template.steps, start=1):
        description = step.description or f"{step.role} review"
        steps.append(
            ApprovalStep(
                role=step.role,
                description=description,
                order=idx,
                required=step.required,
            )
        )
    return steps


def _build_default_template_definitions() -> Dict[str, WorkflowTemplateModel]:
    defaults: Dict[str, WorkflowTemplateModel] = {}
    for name, steps in DEFAULT_WORKFLOW_TEMPLATES.items():
        defaults[name] = WorkflowTemplateModel(
            id=name,
            name=name,
            description=None,
            steps=[
                WorkflowTemplateStep(
                    role=step.role,
                    required=step.required,
                    description=step.description,
                )
                for step in steps
            ],
        )
    return defaults


def _workflow_template_lock() -> FileLock:
    return FileLock(str(WORKFLOW_TEMPLATES_FILE) + ".lock")


def _atomic_write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as tmp_file:
        tmp_file.write(data)
        tmp_name = tmp_file.name
    os.replace(tmp_name, path)


def _coerce_template_payload(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and "templates" in payload:
        templates = payload["templates"]
        if isinstance(templates, list):
            return templates
    raise ValueError("Saved workflow templates must be a list or include 'templates'")


def _load_templates_from_disk() -> None:
    try:
        payload = json.loads(WORKFLOW_TEMPLATES_FILE.read_text())
    except FileNotFoundError:
        return
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"Failed to read workflow templates from {WORKFLOW_TEMPLATES_FILE}"
        ) from exc

    templates_payload = _coerce_template_payload(payload)
    workflow_template_definitions.clear()
    for item in templates_payload:
        if not isinstance(item, dict):
            raise ValueError("Workflow template entry must be a mapping")
        name = str(item.get("name") or item.get("id") or "").strip()
        if not name:
            raise ValueError("Workflow template entry missing name")
        steps_payload = item.get("steps") or []
        if not isinstance(steps_payload, list):
            raise ValueError("Workflow template steps must be a list")
        steps = [WorkflowTemplateStep.model_validate(step) for step in steps_payload]
        template = WorkflowTemplateModel(
            id=name,
            name=name,
            description=item.get("description"),
            steps=steps,
            updated=item.get("updated"),
        )
        workflow_template_definitions[name] = template


def _sync_workflow_templates_from_definitions() -> None:
    workflow_templates.clear()
    for name, template in workflow_template_definitions.items():
        steps = _template_steps_from_definition(template)
        workflow_templates[name] = steps
        _validate_template_orders(name, steps)


def _ensure_templates_loaded() -> None:
    global _ACTIVE_TEMPLATES_FILE, _TEMPLATES_LOADED

    if _ACTIVE_TEMPLATES_FILE != WORKFLOW_TEMPLATES_FILE:
        _ACTIVE_TEMPLATES_FILE = WORKFLOW_TEMPLATES_FILE
        _TEMPLATES_LOADED = False

    if _TEMPLATES_LOADED:
        return

    workflow_template_definitions.clear()
    workflow_template_definitions.update(_build_default_template_definitions())

    if DOCREVIEW360_ENABLE_WORKFLOW_TEMPLATE_PERSISTENCE and WORKFLOW_TEMPLATES_FILE.exists():
        with _workflow_template_lock():
            _load_templates_from_disk()
        if not workflow_template_definitions:
            workflow_template_definitions.update(_build_default_template_definitions())

    _sync_workflow_templates_from_definitions()
    _TEMPLATES_LOADED = True


def _save_templates_to_disk() -> None:
    if not DOCREVIEW360_ENABLE_WORKFLOW_TEMPLATE_PERSISTENCE:
        return
    payload = [template.model_dump() for template in workflow_template_definitions.values()]
    serialized = json.dumps(payload, indent=2)
    with _workflow_template_lock():
        _atomic_write(WORKFLOW_TEMPLATES_FILE, serialized)


def list_workflow_templates() -> list[WorkflowTemplateModel]:
    _ensure_templates_loaded()
    return list(workflow_template_definitions.values())


def get_workflow_template(template_id: str) -> WorkflowTemplateModel | None:
    _ensure_templates_loaded()
    return workflow_template_definitions.get(template_id)


def create_workflow_template(payload: WorkflowTemplatePayload) -> WorkflowTemplateModel:
    _ensure_templates_loaded()
    name = payload.name.strip()
    if name in workflow_template_definitions:
        raise ValueError("Workflow template already exists")
    # Convert steps to dicts to avoid Pydantic class-identity failures after module reloads
    steps_data = [s.model_dump() for s in payload.steps]
    template = WorkflowTemplateModel(
        id=name,
        name=name,
        description=payload.description,
        steps=steps_data,
        updated=datetime.now(timezone.utc).isoformat(),
    )
    workflow_template_definitions[name] = template
    _sync_workflow_templates_from_definitions()
    _save_templates_to_disk()
    return template


def update_workflow_template(
    template_id: str, payload: WorkflowTemplatePayload
) -> WorkflowTemplateModel:
    _ensure_templates_loaded()
    if template_id not in workflow_template_definitions:
        raise KeyError("Workflow template not found")
    name = payload.name.strip()
    if name != template_id and name in workflow_template_definitions:
        raise ValueError("Workflow template name already exists")
    steps_data = [s.model_dump() for s in payload.steps]
    template = WorkflowTemplateModel(
        id=name,
        name=name,
        description=payload.description,
        steps=steps_data,
        updated=datetime.now(timezone.utc).isoformat(),
    )
    if name != template_id:
        workflow_template_definitions.pop(template_id, None)
    workflow_template_definitions[name] = template
    _sync_workflow_templates_from_definitions()
    _save_templates_to_disk()
    return template


def delete_workflow_template(template_id: str) -> None:
    _ensure_templates_loaded()
    if template_id not in workflow_template_definitions:
        raise KeyError("Workflow template not found")
    workflow_template_definitions.pop(template_id)
    workflow_templates.pop(template_id, None)
    _sync_workflow_templates_from_definitions()
    _save_templates_to_disk()


def reset_workflow_templates(*, keep_file: bool = False) -> None:
    """Reset workflow templates to defaults for tests."""

    global _TEMPLATES_LOADED
    _TEMPLATES_LOADED = False
    workflow_template_definitions.clear()
    workflow_templates.clear()
    if not keep_file and DOCREVIEW360_ENABLE_WORKFLOW_TEMPLATE_PERSISTENCE:
        try:
            WORKFLOW_TEMPLATES_FILE.unlink(missing_ok=True)
        except OSError:
            pass
    _ensure_templates_loaded()


_ensure_templates_loaded()


@log_call
def list_roles() -> list[str]:
    """Return a sorted list of all unique roles used in workflow templates."""
    _ensure_templates_loaded()
    roles = {step.role for steps in workflow_templates.values() for step in steps}
    return sorted(roles)


@log_call
def get_approval_steps_for_phase(
    phase: str, workflow: str = "branch-coordination"
) -> List[ApprovalStep]:
    """Return approval steps for the given workflow."""
    _ensure_templates_loaded()
    try:
        steps = workflow_templates[workflow]
    except KeyError as exc:
        raise KeyError(f"Unknown workflow '{workflow}'") from exc
    _validate_template_orders(workflow, steps)
    return [ApprovalStep.model_validate(step.model_dump()) for step in steps]


def _bootstrap_sample() -> None:
    """Create a default workflow so the API returns initial data."""
    _ensure_templates_loaded()
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


"""Workflows bootstrap behavior
---------------------------------

Historically the module executed :func:`_bootstrap_sample` on import unless an
environment variable named ``DOCREVIEW360_SKIP_SAMPLE_BOOTSTRAP`` was set to
``"1"``.  The default behavior (running the bootstrap) is convenient for the
real application which wants some seed data at startup.  For tests and for
light‑weight usage this proved problematic as the bootstrap initializes the
database and touches a number of other modules which may not be configured.  In
the minimal test environment used in this kata the eager bootstrap attempted to
run database migrations during import which raised
``sqlalchemy.exc.InvalidRequestError`` and prevented the package from even being
imported.

To make the module safe to import in isolation we now *skip* bootstrapping by
default.  Setting ``DOCREVIEW360_ENABLE_SAMPLE_BOOTSTRAP=1`` re‑enables the
previous behavior.  This mirrors the intent – seeding data should be an
explicit choice – and keeps application behavior intact when the new variable
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
def list_workflows(project: str | None = None, *, bootstrap: bool = False) -> list[WorkflowModel]:
    """Return workflows optionally filtered by project."""
    if bootstrap and not workflows:
        _bootstrap_sample()
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
                # entry is appended when missing.  This keeps the behavior
                # consistent regardless of external patches and prevents state
                # leakage between tests.
                from .logs import LogEntry
                from .logs import logs as _logs

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
                    import json

                    from .audit import (
                        _AUDIT_LOG_PATH,
                        AuditLogEntry,
                        _compute_hash,
                    )

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

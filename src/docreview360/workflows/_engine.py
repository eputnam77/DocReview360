# SPDX-License-Identifier: MIT
"""Workflow execution engine — create, advance, start, assign, register callbacks."""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Callable, Dict, List
from uuid import uuid4

from ._models import ApprovalStep, WorkflowModel
from ._templates import (
    _ensure_templates_loaded,
    _validate_template_orders,
    workflow_templates,
)

_logger = logging.getLogger(__name__)

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


def _load_bot_callbacks_once() -> None:
    """Add the event dispatcher callback exactly once."""
    from ..event_dispatcher import dispatch_workflow_event

    if dispatch_workflow_event not in bot_callbacks:
        bot_callbacks.append(dispatch_workflow_event)


_load_bot_callbacks_once()


def _persist_workflow(workflow: WorkflowModel) -> None:
    """Upsert a workflow instance into the DB."""
    try:
        from sqlalchemy import text as _text

        from ..db_store import get_db

        db = get_db()
        data = json.dumps(workflow.model_dump())
        with db.session() as conn:
            conn.execute(
                _text(
                    "INSERT INTO workflow_instance_records (id, project, data)"
                    " VALUES (:id, :project, :data)"
                    " ON CONFLICT(id) DO UPDATE SET data=excluded.data"
                ),
                {"id": workflow.id, "project": workflow.project, "data": data},
            )
    except Exception as exc:  # pragma: no cover - best effort
        _logger.warning("Failed to persist workflow %r to DB: %s", workflow.id, exc)


def load_workflows_from_db() -> None:
    """Populate the in-memory ``workflows`` dict from the database."""
    try:
        from sqlalchemy import text as _text

        from ..db_store import get_db

        db = get_db()
        with db.session() as conn:
            rows = conn.execute(
                _text("SELECT data FROM workflow_instance_records")
            ).fetchall()
        for (raw,) in rows:
            data = json.loads(raw) if isinstance(raw, str) else raw
            try:
                wf = WorkflowModel.model_validate(data)
                if wf.id not in workflows:
                    workflows[wf.id] = wf
            except Exception as exc:  # pragma: no cover - skip corrupt rows
                _logger.debug("Skipping corrupt workflow row: %s", exc)
    except Exception as exc:  # pragma: no cover - DB not available
        _logger.warning("Failed to load workflows from DB: %s", exc)


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


def list_roles() -> list[str]:
    """Return a sorted list of all unique roles used in workflow templates."""
    _ensure_templates_loaded()
    roles = {step.role for steps in workflow_templates.values() for step in steps}
    return sorted(roles)


def _bootstrap_sample() -> None:
    """Create a default workflow so the API returns initial data."""
    _ensure_templates_loaded()
    if workflows:
        return

    from ..phases import list_phases

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


# Only perform the sample bootstrap when explicitly enabled.
if os.getenv("DOCREVIEW360_ENABLE_SAMPLE_BOOTSTRAP") == "1":
    _bootstrap_sample()


def register_bot(callback: Callable[[WorkflowModel], None]) -> None:
    """Register an automation bot callback."""
    bot_callbacks.append(callback)


def create_workflow(
    project: str,
    phases: List[str],
    template: str = "branch-coordination",
    mode: str = "sequential",
) -> WorkflowModel:
    """Create a workflow for a project starting at the first phase."""
    wf_id = uuid4().hex
    start_phase = phases[0] if phases else "start"

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
    _persist_workflow(workflow)

    from ..approvals import create_approval

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


def get_workflow(wf_id: str) -> WorkflowModel | None:
    """Return a workflow by id."""
    return workflows.get(wf_id)


def list_workflows(project: str | None = None, *, bootstrap: bool = False) -> list[WorkflowModel]:
    """Return workflows optionally filtered by project."""
    if bootstrap and not workflows:
        _bootstrap_sample()
    if project is None:
        return list(workflows.values())
    return [wf for wf in workflows.values() if wf.project == project]


def register_callback_url(wf_id: str, url: str) -> WorkflowModel:
    """Register a callback URL for workflow events."""
    workflow = workflows[wf_id]
    workflow.callback_url = url
    return workflow


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
    _persist_workflow(workflow)
    for cb in bot_callbacks:
        cb(workflow)
    return workflow


def start_workflow(wf_id: str, title: str, data: bytes | None = None) -> WorkflowModel:
    """Attach a document to the workflow and mark it as started."""

    from ..approvals import approvals as approval_store
    from ..audit import log_audit_event
    from ..documents import import_document, link_approval, unlink_approval
    from ..logs import LogEntry, log_event
    from ..logs import logs as _logs

    workflow = workflows[wf_id]
    filename = title if title.endswith((".md", ".doc", ".docx")) else f"{title}.md"
    content = data or b"-"
    document = import_document(filename, content, project=workflow.project)
    workflow.document = document.id

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
                if audit_entry is None:
                    import json as _json

                    from ..audit import (
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
                        fh.write(_json.dumps(payload) + "\n")

    if workflow.phases:
        workflow.phase = workflow.phases[0]
    return workflow

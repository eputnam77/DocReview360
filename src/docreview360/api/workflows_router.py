# SPDX-License-Identifier: MIT
"""Workflows sub-router: /workflow-templates/*, /workflows/*, /workflow_roles,
/phases/*, /approvals/*, /templates/*, /email-templates/*."""
from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, Header, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel, ConfigDict, Field

from .. import auth
from ..rbac import require_role
from ..approvals import (
    ApprovalModel,
    SignedApprovalImmutableError,
    create_approval,
    delete_approval,
    get_approval,
    list_approvals,
    send_for_signature,
    update_approval_state,
)
from ..audit import log_audit_event
from ..logs import log_event, log_call
from ..phases import (
    add_phase,
    delete_phase,
    get_phase_workflow_template,
    list_phase_workflow_links,
    list_phases,
    list_phases_detail,
    rename_phase,
    set_phase_workflow_template,
)
from ..template_manager import (
    delete_template as delete_stored_template,
    get_latest_template,
    get_template_phase_locks,
    is_template_locked_for_phase,
    list_stored_templates,
    list_template_versions,
    lock_template_for_phase,
    approve_template,
    retire_template,
    unlock_template_for_phase,
    upload_template as store_template,
)
from ..email_templates import (
    create_template as create_email_template,
    delete_template as delete_email_template,
    get_template as get_email_template,
    list_templates as list_email_templates,
    update_template as update_email_template,
)
from ..workflows import (
    WorkflowModel,
    WorkflowTemplateModel,
    WorkflowTemplatePayload,
    WorkflowTemplateStep,
    advance_workflow,
    assign_reviewer,
    create_workflow,
    create_workflow_template,
    delete_workflow_template,
    get_workflow,
    get_workflow_template,
    list_workflows,
    list_workflow_templates,
    start_workflow,
    update_workflow_template,
    workflow_templates,
    workflows,
    list_roles,
)
from ..rbac import has_role
from ..doc_types import get_document_type, list_document_types

_logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class WorkflowCreate(BaseModel):
    """Input model for creating workflows."""

    project: str
    phases: list[str]
    mode: str = "sequential"


class WorkflowTemplateResponse(BaseModel):
    """Response payload for workflow templates."""

    id: str
    name: str
    description: str | None = None
    steps: list[WorkflowTemplateStep]
    updated: str | None = None
    usage: int = 0


class ReviewerAssign(BaseModel):
    """Input model for assigning reviewers."""

    user: str


class ApprovalCreate(BaseModel):
    """Input model for creating approvals."""

    workflow: str
    reviewer: str
    doc_id: str | None = None
    due_at: datetime | None = None
    description: str | None = None
    phase_id: str | None = None
    required: bool | None = None
    role: str | None = None
    order: int = 0
    reminder_at: datetime | None = None
    escalate_to: str | None = None
    escalation_at: datetime | None = None


class ApprovalUpdate(BaseModel):
    """Input model for updating approval state."""

    model_config = ConfigDict(populate_by_name=True)

    state: str
    signature_id: str | None = Field(default=None, alias="signature")
    due_at: datetime | None = None


class SignInitialsBody(BaseModel):
    """Input model for approving via initials signature."""

    initials: str


class PhaseModel(BaseModel):
    """Simple phase schema."""

    name: str


class PhaseWorkflowLinkModel(BaseModel):
    """Rich phase schema — the canonical structured phase response.

    Mirrors the style of ``DocumentTypeModel`` so that both phases and document
    types can be consumed uniformly by clients:

    - ``id`` — stable string identifier (equal to ``name``); used in URLs and
      FK references so clients need not encode the name.
    - ``name`` — human-readable display name.
    - ``display_order`` — sort position (lower = first).
    - ``workflow_template_id`` — linked workflow template if set, else ``None``.
    """

    id: str
    name: str
    display_order: int = 0
    workflow_template_id: str | None = None


class PhaseWorkflowLinkUpdateModel(BaseModel):
    """Payload for setting or clearing a phase's default workflow template."""

    workflow_template_id: str | None = None


class EmailTemplatePayload(BaseModel):
    """Payload for email templates."""

    name: str
    subject: str
    body: str
    task: str | None = None


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _workflow_template_usage(template_id: str) -> int:
    return sum(1 for wf in workflows.values() if wf.template == template_id)


def _serialize_workflow_template(template: WorkflowTemplateModel) -> WorkflowTemplateResponse:
    steps_data = [s.model_dump() for s in template.steps]
    return WorkflowTemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        steps=steps_data,
        updated=template.updated,
        usage=_workflow_template_usage(template.id),
    )


def _serialize_phase_workflow_links() -> list[PhaseWorkflowLinkModel]:
    return [
        PhaseWorkflowLinkModel(
            id=entry["id"],  # type: ignore[arg-type]
            name=entry["name"],  # type: ignore[arg-type]
            display_order=entry["display_order"],  # type: ignore[arg-type]
            workflow_template_id=entry["workflow_template_id"],  # type: ignore[arg-type]
        )
        for entry in list_phases_detail()
    ]


def _normalize_template_metadata(
    metadata: dict[str, Any],
    *,
    doc_type: str | None,
    format_value: str | None,
) -> dict[str, Any]:
    normalized = dict(metadata)
    if doc_type:
        normalized["docType"] = doc_type
        normalized["doc_type"] = doc_type
    if format_value:
        normalized["format"] = format_value.upper()
        normalized["type"] = format_value.lower()
    normalized.setdefault("updated", datetime.now(timezone.utc).isoformat())
    return normalized


def _resolve_format_from_filename(filename: str | None) -> str | None:
    if not filename:
        return None
    parts = filename.rsplit(".", maxsplit=1)
    if len(parts) != 2:
        return None
    return parts[-1].strip().lower()


async def _parse_template_request(  # noqa: C901
    request: Request,
    *,
    fallback_name: str | None = None,
) -> tuple[str, dict[str, Any], bytes]:
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        name = str(form.get("name") or form.get("id") or fallback_name or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="name is required")
        doc_type = form.get("docType") or form.get("doc_type")
        format_value = form.get("format") or form.get("type")
        meta_value = form.get("meta") or "{}"
        content_text = form.get("content")
        try:
            metadata = json.loads(str(meta_value))
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="invalid metadata") from exc
        file = form.get("file")
        content: bytes
        if isinstance(file, UploadFile):
            content = await file.read()
            format_value = format_value or _resolve_format_from_filename(file.filename)
            metadata.setdefault("filename", file.filename)
        elif file is not None:
            if hasattr(file, "read"):
                maybe_content = file.read()
                if asyncio.iscoroutine(maybe_content):
                    maybe_content = await maybe_content
                content = (
                    maybe_content.encode("utf-8")
                    if isinstance(maybe_content, str)
                    else bytes(maybe_content)
                )
            else:
                content = bytes(file)
        elif content_text is not None:
            content = str(content_text).encode("utf-8")
        else:
            raise HTTPException(status_code=400, detail="template content is required")
        metadata = _normalize_template_metadata(
            metadata,
            doc_type=str(doc_type).strip() if doc_type else None,
            format_value=str(format_value).strip() if format_value else None,
        )
        return name, metadata, content

    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="invalid template payload")
    name = str(payload.get("name") or payload.get("id") or fallback_name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    content_text = payload.get("content")
    if content_text is None:
        raise HTTPException(status_code=400, detail="template content is required")
    content = str(content_text).encode("utf-8")
    metadata = payload.get("meta") or {}
    if metadata and not isinstance(metadata, dict):
        raise HTTPException(status_code=400, detail="meta must be a mapping")
    doc_type = payload.get("docType") or payload.get("doc_type")
    format_value = payload.get("format") or payload.get("type")
    metadata = _normalize_template_metadata(
        metadata,
        doc_type=str(doc_type).strip() if doc_type else None,
        format_value=str(format_value).strip() if format_value else None,
    )
    return name, metadata, content


def _seed_default_email_templates() -> None:
    """Seed email templates used by notifications when missing."""
    defaults = [
        {"name": "approval_complete", "subject": "Approval complete: {document_title}", "body": "Approval complete for {document_title}.", "task": "approval"},
        {"name": "approval_request", "subject": "Approval requested: {document_title}", "body": "Please approve {document_title}. {action_url}", "task": "approval"},
        {"name": "comment_added", "subject": "New comment: {document_title}", "body": "{commenter} commented: {comment}. {action_url}", "task": "comment"},
        {"name": "completion_notice", "subject": "{item} complete", "body": "Completed: {item}.", "task": "notification"},
        {"name": "default", "subject": "{subject}", "body": "{body}", "task": "system"},
        {"name": "due_reminder", "subject": "{item} due {due_date}", "body": "Due {due_date}: {item}.", "task": "reminder"},
        {"name": "overdue_notice", "subject": "{item} overdue", "body": "Overdue: {item}. {action_url}", "task": "reminder"},
        {"name": "phase_changed", "subject": "Phase update: {project_name}", "body": "{project_name} moved to {phase}.", "task": "status"},
        {"name": "project_assigned", "subject": "Project assigned: {project_name}", "body": "You are assigned to {project_name}. {action_url}", "task": "assignment"},
        {"name": "review_complete", "subject": "Review complete: {document_title}", "body": "Review complete for {document_title}.", "task": "review"},
        {"name": "review_request", "subject": "Review requested: {document_title}", "body": "Please review {document_title}. {action_url}", "task": "review"},
        {"name": "signature_request", "subject": "Signature requested: {document_title}", "body": "Please sign {document_title}. {action_url}", "task": "signature"},
    ]
    for tmpl in defaults:
        existing = get_email_template(tmpl["name"])
        if existing is not None:
            if not existing.subject.strip() or not existing.body.strip():
                try:
                    update_email_template(tmpl["name"], subject=tmpl["subject"], body=tmpl["body"], task=tmpl.get("task"))
                except Exception:
                    continue
            continue
        try:
            create_email_template(tmpl["name"], tmpl["subject"], tmpl["body"], task=tmpl.get("task"))
        except Exception:
            continue


def _seed_default_document_templates() -> None:
    """Seed one TipTap HTML template per document type when missing."""
    for doc_type in list_document_types():
        name = f"doc_type::{doc_type.name.strip()}"
        if get_latest_template(name):
            continue
        content = doc_type.template or f"<h1>{doc_type.name}</h1>"
        metadata = {
            "label": f"{doc_type.name} (Default)",
            "docType": doc_type.name,
            "format": "HTML",
            "type": "tiptap",
            "description": f"Default template for {doc_type.name} documents.",
            "default": True,
        }
        store_template(name, content.encode("utf-8"), metadata)
        try:
            approve_template(name)
        except Exception as _approve_exc:
            _logger.warning("Failed to auto-approve seeded template '%s': %s", name, _approve_exc)


# ---------------------------------------------------------------------------
# Internal phase helpers
# ---------------------------------------------------------------------------

def _ensure_phase_exists(name: str, phases_list: list[str]) -> None:
    if name not in phases_list:
        raise HTTPException(status_code=404, detail=f"Phase '{name}' not found")


def _validate_replacement_exists(replacement: str | None, phases_list: list[str]) -> None:
    if replacement and replacement not in phases_list:
        raise HTTPException(status_code=404, detail=f"Replacement phase '{replacement}' not found")


def _phase_usage(name: str) -> tuple[list[Any], list[WorkflowModel]]:
    all_wfs = list_workflows()
    workflows_using_phase = [w for w in all_wfs if name in w.phases]

    from ..search import list_projects, get_project as _get_project
    projects_using_phase: list[Any] = []
    for project in list_projects():
        if project.workflow:
            workflow = get_workflow(project.workflow)
            if workflow and name in workflow.phases:
                projects_using_phase.append(project)
    return projects_using_phase, workflows_using_phase


def _apply_phase_replacement(name: str, replacement: str, workflows_using_phase: list[WorkflowModel]) -> None:
    for wf in workflows_using_phase:
        wf.phases = [replacement if p == name else p for p in wf.phases]
        if wf.phase == name:
            wf.phase = replacement


# ---------------------------------------------------------------------------
# Phase routes
# ---------------------------------------------------------------------------

@router.post("/phases", status_code=201, response_model=list[str])
async def create_phase_endpoint(
    body: PhaseModel,
    _user: auth.User = Depends(require_role("admin")),
) -> list[str]:
    """Create a new project phase (admin only)."""
    add_phase(body.name)
    return list_phases()


@router.get("/phases", response_model=list[str])
async def list_phases_endpoint() -> list[str]:
    """Return all configured phases."""
    return list_phases()


@router.get("/phases/config", response_model=list[PhaseWorkflowLinkModel])
async def list_phase_config_endpoint() -> list[PhaseWorkflowLinkModel]:
    """Return phases and their optional default workflow-template links."""
    return _serialize_phase_workflow_links()


@router.put(
    "/phases/{name}/workflow-template",
    response_model=PhaseWorkflowLinkModel,
)
async def set_phase_workflow_template_endpoint(
    name: str,
    body: PhaseWorkflowLinkUpdateModel,
    _user: auth.User = Depends(require_role("admin")),
) -> PhaseWorkflowLinkModel:
    """Set or clear the default workflow template associated with a phase (admin only)."""
    phases_list = list_phases()
    if name not in phases_list:
        raise HTTPException(status_code=404, detail=f"Phase '{name}' not found")

    template_id = (
        body.workflow_template_id.strip()
        if isinstance(body.workflow_template_id, str)
        else None
    )

    if template_id and get_workflow_template(template_id) is None:
        raise HTTPException(status_code=404, detail="Workflow template not found")

    try:
        set_phase_workflow_template(name, template_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    detail = next(
        (e for e in list_phases_detail() if e["name"] == name),
        None,
    )
    return PhaseWorkflowLinkModel(
        id=name,
        name=name,
        display_order=int(detail["display_order"]) if detail else 0,
        workflow_template_id=get_phase_workflow_template(name),
    )


@router.put("/phases/{name}", response_model=list[str])
async def rename_phase_endpoint(
    name: str,
    body: PhaseModel,
    _user: auth.User = Depends(require_role("admin")),
) -> list[str]:
    """Rename a phase and propagate changes to workflows (admin only)."""
    phases_list = list_phases()
    if name not in phases_list:
        raise HTTPException(status_code=404, detail=f"Phase '{name}' not found")

    try:
        rename_phase(name, body.name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    all_workflows = list_workflows()
    for wf in all_workflows:
        wf.phases = [body.name if p == name else p for p in wf.phases]
        if wf.phase == name:
            wf.phase = body.name

    from ..search import projects
    for proj in projects.values():
        if getattr(proj, "initial_phase", None) == name:
            proj.initial_phase = body.name

    return list_phases()


@router.get("/phases/{name}/usage", response_model=dict[str, Any])
async def check_phase_usage_endpoint(
    name: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Check if a phase is in use and return usage information."""
    phases_list = list_phases()
    if name not in phases_list:
        raise HTTPException(status_code=404, detail=f"Phase '{name}' not found")

    all_wfs = list_workflows()
    workflows_using_phase = [w for w in all_wfs if name in w.phases]

    from ..search import list_projects as _list_projects
    projects_using_phase = []
    for project in _list_projects():
        if project.workflow:
            workflow = get_workflow(project.workflow)
            if workflow and name in workflow.phases:
                projects_using_phase.append(project)

    return {
        "name": name,
        "in_use": len(projects_using_phase) > 0 or len(workflows_using_phase) > 0,
        "usage_count": len(projects_using_phase) + len(workflows_using_phase),
        "projects": [{"id": p.id, "name": p.name} for p in projects_using_phase],
        "workflows": [{"id": w.id, "project": w.project} for w in workflows_using_phase],
    }


@router.delete("/phases/{name}", status_code=204, response_class=Response)
async def delete_phase_endpoint(
    name: str,
    replacement: str | None = None,
    _user: auth.User = Depends(require_role("admin")),
) -> Response:
    """Remove a phase by name (admin only). If in use, replacement is required."""
    phases_list = list_phases()
    _ensure_phase_exists(name, phases_list)
    _validate_replacement_exists(replacement, phases_list)

    projects_using_phase, workflows_using_phase = _phase_usage(name)

    if projects_using_phase or workflows_using_phase:
        if not replacement:
            detail_msg = (
                f"Phase '{name}' is in use by {len(projects_using_phase)} "
                f"project(s) and {len(workflows_using_phase)} workflow(s). "
                "Please specify a replacement phase."
            )
            raise HTTPException(status_code=400, detail=detail_msg)
        if replacement == name:
            raise HTTPException(status_code=400, detail="Replacement phase must be different")
        _apply_phase_replacement(name, replacement, workflows_using_phase)

    try:
        delete_phase(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)


@router.get("/phases/sla", response_model=dict[str, Any])
async def list_phase_slas_endpoint(
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Return all configured per-phase SLA definitions."""
    from ..phase_sla import get_all_phase_slas
    slas = get_all_phase_slas()
    return {"slas": {phase: cfg.model_dump() for phase, cfg in slas.items()}}


@router.get("/phases/{name}/sla", response_model=dict[str, Any])
async def get_phase_sla_endpoint(
    name: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Return the SLA configuration for a specific phase."""
    from ..phase_sla import get_phase_sla
    cfg = get_phase_sla(name)
    if cfg is None:
        raise HTTPException(status_code=404, detail=f"No SLA configured for phase '{name}'")
    return cfg.model_dump()


@router.put("/phases/{name}/sla", response_model=dict[str, Any])
async def set_phase_sla_endpoint(
    name: str,
    max_days: int = Body(..., embed=True, gt=0),
    warning_days: int = Body(..., embed=True, ge=0),
    user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Create or update the SLA configuration for a phase."""
    from ..phase_sla import set_phase_sla
    try:
        cfg = set_phase_sla(name, max_days=max_days, warning_days=warning_days)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    log_audit_event(
        f"phase::{name}",
        "sla_updated",
        actor=user.username,
        max_days=max_days,
        warning_days=warning_days,
    )
    return cfg.model_dump()


@router.delete("/phases/{name}/sla", status_code=204, response_class=Response)
async def delete_phase_sla_endpoint(
    name: str,
    user: auth.User = Depends(require_role("admin")),
) -> Response:
    """Remove the SLA configuration for a phase."""
    from ..phase_sla import delete_phase_sla
    existed = delete_phase_sla(name)
    if not existed:
        raise HTTPException(status_code=404, detail=f"No SLA configured for phase '{name}'")
    return Response(status_code=204)


@router.get("/phases/{name}/sla/status", response_model=dict[str, Any])
async def evaluate_phase_sla_endpoint(
    name: str,
    elapsed_days: int,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Evaluate the SLA status for a phase given elapsed days."""
    from ..phase_sla import evaluate_phase_sla
    result = evaluate_phase_sla(name, elapsed_days)
    return result.model_dump()


# ---------------------------------------------------------------------------
# Workflow template routes
# ---------------------------------------------------------------------------

@router.get("/workflow-templates", response_model=list[WorkflowTemplateResponse])
@log_call
async def list_workflow_templates_endpoint(
    x_user: str | None = Header(None),
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[WorkflowTemplateResponse]:
    """Return workflow templates for the admin UI."""
    return [_serialize_workflow_template(t) for t in list_workflow_templates()]


@router.post("/workflow-templates", status_code=201, response_model=WorkflowTemplateResponse)
@log_call
async def create_workflow_template_endpoint(
    body: WorkflowTemplatePayload,
    x_user: str | None = Header(None),
    current_user: auth.User = Depends(auth.get_current_user),
) -> WorkflowTemplateResponse:
    """Create a workflow template."""
    try:
        template = create_workflow_template(body)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _serialize_workflow_template(template)


@router.get("/workflow-templates/{template_id}", response_model=WorkflowTemplateResponse)
@log_call
async def get_workflow_template_endpoint(
    template_id: str,
    x_user: str | None = Header(None),
    current_user: auth.User = Depends(auth.get_current_user),
) -> WorkflowTemplateResponse:
    """Return workflow template by id."""
    template = get_workflow_template(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Workflow template not found")
    return _serialize_workflow_template(template)


@router.put("/workflow-templates/{template_id}", response_model=WorkflowTemplateResponse)
@log_call
async def update_workflow_template_endpoint(
    template_id: str,
    body: WorkflowTemplatePayload,
    x_user: str | None = Header(None),
    current_user: auth.User = Depends(auth.get_current_user),
) -> WorkflowTemplateResponse:
    """Update workflow template by id."""
    try:
        template = update_workflow_template(template_id, body)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _serialize_workflow_template(template)


@router.delete("/workflow-templates/{template_id}", status_code=204, response_class=Response)
@log_call
async def delete_workflow_template_endpoint(
    template_id: str,
    x_user: str | None = Header(None),
    current_user: auth.User = Depends(auth.get_current_user),
) -> Response:
    """Delete workflow template by id."""
    try:
        delete_workflow_template(template_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Workflow routes
# ---------------------------------------------------------------------------

@router.post("/workflows", status_code=201, response_model=WorkflowModel)
@log_call
async def create_workflow_endpoint(
    workflow: WorkflowCreate,
    x_user: str | None = Header(None),
    current_user: auth.User = Depends(auth.get_current_user),
) -> WorkflowModel:
    """Create a new workflow."""
    return create_workflow(workflow.project, workflow.phases, mode=workflow.mode)


@router.get("/workflows/{wf_id}", response_model=WorkflowModel)
@log_call
async def get_workflow_endpoint(
    wf_id: str,
    x_user: str | None = Header(None),
    current_user: auth.User = Depends(auth.get_current_user),
) -> WorkflowModel:
    """Return a workflow by id."""
    wf = get_workflow(wf_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


@router.get("/workflows", response_model=list[WorkflowModel])
@log_call
async def list_workflows_endpoint(
    project: str | None = None,
    x_user: str | None = Header(None),
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[WorkflowModel]:
    """Return workflows optionally filtered by project."""
    return list_workflows(project, bootstrap=True)


@router.get("/workflow_roles", response_model=list[str])
@log_call
async def list_workflow_roles_endpoint(
    x_user: str | None = Header(None),
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[str]:
    """Return all unique workflow roles."""
    return list_roles()


@router.post("/workflows/{wf_id}/start", response_model=WorkflowModel)
@log_call
async def start_workflow_endpoint(
    wf_id: str,
    title: str | None = Form(None),
    file: UploadFile | None = File(None),
    x_user: str | None = Header(None),
    current_user: auth.User = Depends(auth.get_current_user),
) -> WorkflowModel:
    """Start a workflow by uploading a document."""
    wf = get_workflow(wf_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if title is None or not title.strip():
        title = wf.project or f"workflow-{wf_id}"
    data = await file.read() if file else None
    return start_workflow(wf_id, title, data)


@router.post("/workflows/{wf_id}/assign", response_model=WorkflowModel)
@log_call
async def assign_reviewer_endpoint(
    wf_id: str,
    body: ReviewerAssign,
    x_user: str | None = Header(None),
    current_user: auth.User = Depends(auth.get_current_user),
) -> WorkflowModel:
    """Assign a reviewer to a workflow."""
    try:
        return assign_reviewer(wf_id, body.user)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/workflows/{wf_id}/advance", response_model=WorkflowModel)
@log_call
async def advance_workflow_endpoint(
    wf_id: str,
    x_user: str | None = Header(None),
    current_user: auth.User = Depends(auth.get_current_user),
) -> WorkflowModel:
    """Advance workflow to the next phase."""
    try:
        return advance_workflow(wf_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Approval routes (inline, not from approvals_router)
# ---------------------------------------------------------------------------

@router.post("/approvals", status_code=201, response_model=ApprovalModel)
@log_call
async def create_approval_endpoint(
    body: ApprovalCreate,
    current_user: auth.User = Depends(auth.get_current_user),
) -> ApprovalModel:
    """Create an approval for a workflow."""
    return create_approval(
        body.workflow,
        body.reviewer,
        body.doc_id,
        due_at=body.due_at,
        description=body.description,
        phase_id=body.phase_id,
        required=body.required if body.required is not None else True,
        role=body.role,
        order=body.order,
        reminder_at=body.reminder_at,
        escalate_to=body.escalate_to,
        escalation_at=body.escalation_at,
    )


@router.get("/approvals", response_model=list[ApprovalModel])
@log_call
async def list_approvals_endpoint(
    workflow: str | None = None,
    phase: str | None = None,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[ApprovalModel]:
    """Return approvals optionally filtered by workflow and phase."""
    return list_approvals(workflow, phase)


@router.get("/approvals/{approval_id}", response_model=ApprovalModel)
@log_call
async def get_approval_endpoint(
    approval_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> ApprovalModel:
    """Retrieve a single approval by id."""
    approval = get_approval(approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    return approval


@router.put("/approvals/{approval_id}", response_model=ApprovalModel)
@log_call
async def update_approval_endpoint(
    approval_id: str,
    body: ApprovalUpdate,
    current_user: auth.User = Depends(auth.get_current_user),
) -> ApprovalModel:
    """Update approval state and signature."""
    try:
        return await update_approval_state(
            approval_id,
            body.state,
            signature_id=body.signature_id,
            due_at=body.due_at,
        )
    except SignedApprovalImmutableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/approvals/{approval_id}", response_model=ApprovalModel)
@log_call
async def delete_approval_endpoint(
    approval_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> ApprovalModel:
    """Delete an approval by id."""
    try:
        return delete_approval(approval_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/approvals/{approval_id}/sign")
@log_call
async def sign_approval_endpoint(
    approval_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, str]:
    """Begin a signing flow for an approval."""
    approval = get_approval(approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    wf = get_workflow(approval.workflow)
    if wf is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return_to = f"/projects/{wf.project}"
    doc_id = approval.document_id or wf.project
    try:
        url = send_for_signature(approval_id, doc_id, approval.reviewer, return_to)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    sig_id = approval.signature_id
    if sig_id is None:
        raise RuntimeError("signature id not set")
    return {"id": sig_id, "url": url}


@router.post("/approvals/{approval_id}/sign-initials", response_model=ApprovalModel)
@log_call
async def sign_initials_endpoint(
    approval_id: str,
    body: SignInitialsBody,
    current_user: auth.User = Depends(auth.get_current_user),
) -> ApprovalModel:
    """Approve an approval by recording reviewer initials as the signature."""
    if not re.fullmatch(r"[A-Z]{2,5}", body.initials):
        raise HTTPException(
            status_code=422,
            detail="Initials must be 2–5 uppercase letters (A–Z) with no spaces or numbers.",
        )
    approval = get_approval(approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    try:
        return await update_approval_state(
            approval_id,
            "approved",
            signature_id=f"[initials:{body.initials}]",
        )
    except SignedApprovalImmutableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Template routes
# ---------------------------------------------------------------------------

@router.get("/templates")
async def list_templates_endpoint(
    request: Request,
    user: auth.User = Depends(auth.get_current_user),
) -> list[dict[str, Any]]:
    _seed_default_document_templates()
    items: list[dict[str, Any]] = []
    is_admin = has_role(user.username, "admin")
    for name, ver in list_stored_templates().items():
        if not is_admin and (not ver.approved or ver.retired):
            continue
        meta = ver.metadata
        format_value = meta.get("format")
        type_value = meta.get("type")
        label = meta.get("label") or name
        description = meta.get("description")
        if not description and meta.get("docType"):
            description = f"Document type: {meta.get('docType')}"
        url = None
        if request is not None and "/" not in name:
            url = str(request.url_for("download_template_endpoint", name=name))
        data = {
            "id": name,
            "name": name,
            "version": ver.version,
            "approved": ver.approved,
            "retired": ver.retired,
            "format": format_value,
            "type": type_value or (format_value.lower() if isinstance(format_value, str) else None),
            "label": label,
            "description": description,
            "url": url,
        }
        data.update(meta)
        items.append(data)
    return items


@router.get("/templates/{name}")
async def get_template_endpoint(
    name: str,
    user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    ver = get_latest_template(name)
    if not ver:
        raise HTTPException(status_code=404, detail="template not found")
    data: dict[str, Any] = {
        "id": name,
        "name": name,
        "version": ver.version,
        "content": ver.content.decode("utf-8", errors="ignore"),
        "approved": ver.approved,
        "retired": ver.retired,
    }
    data.update(ver.metadata)
    return data


@router.post("/templates", status_code=201)
async def upload_template_endpoint(
    request: Request,
    user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Store uploaded template content with metadata."""
    name, metadata, content = await _parse_template_request(request)
    version = store_template(name, content, metadata)
    return {
        "name": name,
        "version": version.version,
        "metadata": version.metadata,
        "approved": version.approved,
        "retired": version.retired,
    }


@router.put("/templates/{name}")
async def update_template_endpoint(
    name: str,
    request: Request,
    user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Update stored template content by creating a new version."""
    updated_name, metadata, content = await _parse_template_request(request, fallback_name=name)
    if updated_name != name:
        try:
            delete_stored_template(name)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    version = store_template(updated_name, content, metadata)
    return {
        "name": updated_name,
        "version": version.version,
        "metadata": version.metadata,
        "approved": version.approved,
        "retired": version.retired,
    }


@router.delete("/templates/{name}", status_code=204, response_class=Response)
async def delete_template_endpoint(
    name: str,
    user: auth.User = Depends(require_role("admin")),
) -> Response:
    """Remove a stored template."""
    try:
        delete_stored_template(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)


@router.get("/templates/{name}/download", response_class=Response, name="download_template_endpoint")
async def download_template_endpoint(
    name: str,
    user: auth.User = Depends(auth.get_current_user),
) -> Response:
    """Download the latest template file."""
    ver = get_latest_template(name)
    if not ver:
        raise HTTPException(status_code=404, detail="template not found")
    metadata = ver.metadata or {}
    format_value = metadata.get("format") or metadata.get("type") or "txt"
    format_lower = str(format_value).lower()
    extension = {
        "docx": "docx",
        "word": "docx",
        "html": "html",
        "json": "json",
        "xml": "xml",
        "txt": "txt",
        "md": "md",
        "markdown": "md",
    }.get(format_lower, format_lower)
    content_type = {
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "html": "text/html",
        "json": "application/json",
        "xml": "application/xml",
        "txt": "text/plain",
        "md": "text/markdown",
    }.get(extension, "application/octet-stream")
    filename = metadata.get("filename") or f"{name}.{extension}"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=ver.content, media_type=content_type, headers=headers)


@router.post("/templates/{name}/approve")
async def approve_template_endpoint(
    name: str, user: auth.User = Depends(require_role("admin"))
) -> dict[str, Any]:
    ver = approve_template(name)
    return {"name": name, "version": ver.version, "approved": ver.approved}


@router.post("/templates/{name}/retire")
async def retire_template_endpoint(
    name: str, user: auth.User = Depends(require_role("admin"))
) -> dict[str, Any]:
    ver = retire_template(name)
    return {"name": name, "version": ver.version, "retired": ver.retired}


@router.put("/templates/{name}/locks/{phase}")
async def lock_template_phase_endpoint(
    name: str,
    phase: str,
    user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Lock template *name* for *phase*, preventing uploads while that phase is active."""
    lock_template_for_phase(name, phase)
    return {"template": name, "phase": phase, "locked": True}


@router.delete("/templates/{name}/locks/{phase}", status_code=204, response_class=Response)
async def unlock_template_phase_endpoint(
    name: str,
    phase: str,
    user: auth.User = Depends(require_role("admin")),
) -> Response:
    """Remove the phase lock on template *name* for *phase*."""
    unlock_template_for_phase(name, phase)
    return Response(status_code=204)


@router.get("/templates/{name}/locks")
async def list_template_locks_endpoint(
    name: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Return all phases that currently lock template *name*."""
    phases = get_template_phase_locks(name)
    return {"template": name, "locked_phases": phases}


@router.get("/templates/{name}/versions")
async def list_template_versions_endpoint(
    name: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[dict[str, Any]]:
    """Return version history for template *name*, including change summaries."""
    versions = list_template_versions(name)
    if not versions:
        raise HTTPException(status_code=404, detail=f"Template '{name}' not found")
    return [
        {
            "version": v.version,
            "approved": v.approved,
            "retired": v.retired,
            "change_summary": v.change_summary,
            "metadata": v.metadata,
        }
        for v in versions
    ]


# ---------------------------------------------------------------------------
# Email template routes
# ---------------------------------------------------------------------------

@router.get("/email-templates")
async def list_email_templates_endpoint(
    user: auth.User = Depends(require_role("admin")),
) -> list[dict[str, Any]]:
    _seed_default_email_templates()
    tmpl_list = sorted(list_email_templates(), key=lambda t: t.name.lower())
    return [
        {
            "name": tmpl.name,
            "subject": tmpl.subject,
            "body": tmpl.body,
            "task": tmpl.task,
        }
        for tmpl in tmpl_list
    ]


@router.get("/email-templates/{name}")
async def get_email_template_endpoint(
    name: str,
    user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    tmpl = get_email_template(name)
    if tmpl is None:
        raise HTTPException(status_code=404, detail="email template not found")
    return {
        "name": tmpl.name,
        "subject": tmpl.subject,
        "body": tmpl.body,
        "task": tmpl.task,
    }


@router.post("/email-templates", status_code=201)
async def create_email_template_endpoint(
    body: EmailTemplatePayload,
    user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    try:
        tmpl = create_email_template(body.name, body.subject, body.body, task=body.task)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "name": tmpl.name,
        "subject": tmpl.subject,
        "body": tmpl.body,
        "task": tmpl.task,
    }


@router.put("/email-templates/{name}")
async def update_email_template_endpoint(
    name: str,
    body: EmailTemplatePayload,
    user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    if name != body.name:
        raise HTTPException(status_code=400, detail="template name mismatch")
    try:
        tmpl = update_email_template(name, subject=body.subject, body=body.body, task=body.task)
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "name": tmpl.name,
        "subject": tmpl.subject,
        "body": tmpl.body,
        "task": tmpl.task,
    }


@router.delete("/email-templates/{name}", status_code=204, response_class=Response)
async def delete_email_template_endpoint(
    name: str,
    user: auth.User = Depends(require_role("admin")),
) -> Response:
    try:
        delete_email_template(name)
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)

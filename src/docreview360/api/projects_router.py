# SPDX-License-Identifier: MIT
"""Projects sub-router: all /projects/* routes."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from pydantic import BaseModel

from .. import auth
from ..cache import cache_get, cache_set, clear_cache
from ..rbac import has_role


def _emit_webhook(event: str, data: dict) -> None:
    """Best-effort lifecycle webhook emission — never raises."""
    try:
        from .webhooks import emit_lifecycle_event
        emit_lifecycle_event(event, data)  # type: ignore[arg-type]
    except Exception:
        pass
from ..approvals import build_approvals_summary_pdf
from ..audit import log_audit_event
from ..doc_types import get_document_type
from ..doc_validation import score_plain_language
from ..documents import DocumentModel, import_document, list_documents
from ..logs import log_event
from ..messages import render
from ..project_preferences import (
    ProjectPreferences,
    get_project_preferences,
    update_project_preferences,
)
from ..quality import (
    QUALITY_FLAG_NAMES,
    QualityAssessment,
    high_risk_warnings,
    quality_assessment,
)
from ..reviews import ReviewCreate, ReviewModel, add_review, list_reviews
from ..search import (
    ProjectModel,
    add_project,
    add_project_reviewer,
    assign_temporary,
    get_project,
    list_projects,
    remove_project,
    remove_project_reviewer,
    set_project_priority,
    update_project,
    update_project_reviewer,
)
from ..workflows import (
    WorkflowModel,
    create_workflow,
    workflow_templates,
    workflows,
)

_logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Shared helper functions
# ---------------------------------------------------------------------------

def _is_admin_user(user: auth.User) -> bool:
    return has_role(user.username, "admin")


def _resolve_requested_user(requested_user: str | None, current_user: auth.User) -> str:
    """Return an actor user while preventing non-admin impersonation."""
    candidate = (requested_user or "").strip()
    if not candidate:
        return current_user.username
    if candidate != current_user.username and not _is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    return candidate


def _ensure_reviewer_exists(reviewer: str) -> None:
    repo = auth._get_user_repository()
    if not repo.get_user(reviewer):
        raise HTTPException(status_code=404, detail="Reviewer not found")


def _get_user_org_id(username: str) -> int | None:
    """Return the organization ID for ``username``, or None if unassigned."""
    try:
        from ..organizations import get_user_org
        org = get_user_org(username=username)
        return org.get("id") if org else None
    except Exception:
        return None


def _enforce_project_access(project: ProjectModel, current_user: auth.User) -> None:
    """Ensure ``current_user`` can access ``project``.

    Multi-tenant isolation: when the project has an ``org_id``, the requesting
    user must either be an admin or belong to the same organization.
    """
    if _is_admin_user(current_user):
        return
    # Org-scoped isolation check: reject cross-org access
    if project.org_id is not None:
        user_org = _get_user_org_id(current_user.username)
        if user_org != project.org_id:
            raise HTTPException(status_code=403, detail="Forbidden")
        return  # org membership is sufficient for read access
    if project.user == current_user.username:
        return
    if project.temp_user == current_user.username:
        return
    if current_user.username in project.reviewers:
        return
    if any(p.id == project.id for p in list_projects(current_user.username)):
        return
    raise HTTPException(status_code=403, detail="Forbidden")


def _enforce_project_manage_access(project: ProjectModel, current_user: auth.User) -> None:
    """Ensure ``current_user`` can mutate ``project`` assignments and settings.

    For org-scoped projects, only admins may manage the project.
    """
    if _is_admin_user(current_user):
        return
    # Cross-org management is always denied for non-admins
    if project.org_id is not None:
        user_org = _get_user_org_id(current_user.username)
        if user_org != project.org_id:
            raise HTTPException(status_code=403, detail="Forbidden")
    if project.user == current_user.username:
        return
    if project.temp_user == current_user.username:
        return
    raise HTTPException(status_code=403, detail="Forbidden")


def _resolve_project_phases(doc_type_name: str | None, phase: str | None) -> list[str]:
    """Return workflow phases based on document type and optional phase."""
    doc_type_obj = get_document_type(doc_type_name) if doc_type_name else None
    phases: list[str] = list(doc_type_obj.phases) if doc_type_obj else []

    if phase:
        if phases:
            if phase in phases:
                idx = phases.index(phase)
                phases = phases[idx:] + phases[:idx]
            else:
                phases = [phase] + [p for p in phases if p != phase]
        else:
            phases = [phase]

    if not phases:
        phases = [phase or "start"]

    return phases


def _resolve_workflow_template(
    requested_template: str | None,
    doc_type_name: str | None,
    phase_name: str | None = None,
) -> str:
    """Resolve a workflow template using request, doc type default, and phase linkage."""
    from ..phases import get_phase_workflow_template

    if requested_template in workflow_templates:
        return requested_template

    doc_type_obj = get_document_type(doc_type_name) if doc_type_name else None
    doc_default_template = (
        doc_type_obj.default_workflow_template_id
        if doc_type_obj and doc_type_obj.default_workflow_template_id
        else None
    )
    if doc_default_template in workflow_templates:
        return doc_default_template

    if phase_name:
        phase_default_template = get_phase_workflow_template(phase_name)
        if phase_default_template in workflow_templates:
            return phase_default_template

    return "branch-coordination"


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ProjectCreate(BaseModel):
    """Input model for creating projects."""

    id: str | None = None
    name: str
    document_number: str | None = None
    user: str | None = None
    # Optional organization scoping — if omitted the creator's org is used.
    org_id: int | None = None
    doc_type: str | None = None
    phase: str | None = None
    workflow: str | None = None
    priority: int = 0
    description: str | None = None
    # NARA records management fields
    nara_schedule_number: str | None = None
    nara_disposition_authority: str | None = None
    nara_retention_period: str | None = None
    nara_record_series: str | None = None


class ProjectUpdate(BaseModel):
    """Fields allowed when updating a project."""

    name: str | None = None
    user: str | None = None
    doc_type: str | None = None
    phase: str | None = None
    workflow: str | None = None
    description: str | None = None
    # NARA records management fields
    nara_schedule_number: str | None = None
    nara_disposition_authority: str | None = None
    nara_retention_period: str | None = None
    nara_record_series: str | None = None


class ProjectReviewerPayload(BaseModel):
    """Input model for managing project reviewers."""

    reviewer: str


class PriorityUpdate(BaseModel):
    """Input for updating project priority."""

    priority: int


class TemporaryAssign(BaseModel):
    """Input for temporary reassignment."""

    user: str
    until: datetime


class WatchBody(BaseModel):
    user: str


# ---------------------------------------------------------------------------
# Helper functions for project update
# ---------------------------------------------------------------------------

async def _parse_update_body(request: Request) -> tuple[ProjectUpdate | None, bool]:
    """Return the JSON body and whether the workflow field was provided."""
    if request.headers.get("content-type", "").startswith("application/json"):
        data = await request.json()
        return ProjectUpdate(**data), "workflow" in data
    return None, False


def _resolve_workflow(
    request: Request,
    workflow_provided: bool,
    workflow: str | None,
    body: ProjectUpdate | None,
    project_id: str,
    doc_type_name: str | None,
    existing_workflow_id: str | None = None,
) -> tuple[str | None, bool]:
    """Determine new workflow information from the request."""

    def _create_from_template(template_or_workflow: str, phase: str | None) -> tuple[str, bool]:
        phases = _resolve_project_phases(doc_type_name, phase)
        template_name = _resolve_workflow_template(template_or_workflow, doc_type_name, phase)
        wf = create_workflow(project_id, phases, template=template_name)
        return wf.id, True

    is_json = request.headers.get("content-type", "").startswith("application/json")
    requested_template = isinstance(workflow, str) and workflow in workflow_templates

    if is_json:
        if workflow_provided:
            if workflow is not None:
                if requested_template:
                    if existing_workflow_id:
                        current = workflows.get(existing_workflow_id)
                        if (
                            current is not None
                            and current.project == project_id
                            and current.template == workflow
                        ):
                            return current.id, True
                    return _create_from_template(
                        workflow,
                        body.phase if body and body.phase else None,
                    )

                existing_workflow = workflows.get(workflow)
                if existing_workflow is not None:
                    if existing_workflow.project and existing_workflow.project != project_id:
                        raise ValueError("Workflow already assigned to another project")
                    existing_workflow.project = project_id
                    return existing_workflow.id, True
                return _create_from_template(
                    workflow,
                    body.phase if body and body.phase else None,
                )
            return None, True
        return None, False

    if workflow is not None:
        if requested_template:
            if existing_workflow_id:
                current = workflows.get(existing_workflow_id)
                if (
                    current is not None
                    and current.project == project_id
                    and current.template == workflow
                ):
                    return current.id, True
            return _create_from_template(workflow, None)

        existing_workflow = workflows.get(workflow)
        if existing_workflow is not None:
            if existing_workflow.project and existing_workflow.project != project_id:
                raise ValueError("Workflow already assigned to another project")
            existing_workflow.project = project_id
            return existing_workflow.id, True
        return _create_from_template(workflow, None)

    return None, False


def _update_workflow_phase(
    request: Request,
    body: ProjectUpdate | None,
    updated_project: ProjectModel,
    *,
    project_id: str = "",
    archived_by: str = "",
) -> None:
    """Update an existing workflow's phase when only the phase is provided.

    When the phase advances, open feedback items from the previous phase are
    automatically archived (resolved) so the ledger stays clean.
    """
    if not body or body.phase is None:
        return
    is_json = request.headers.get("content-type", "").startswith("application/json")
    if not is_json:
        return
    from ..workflows import get_workflow as _get_wf

    wf_id_to_update = updated_project.workflow
    if not wf_id_to_update:
        return
    wf_model = _get_wf(wf_id_to_update)
    if wf_model:
        old_phase = wf_model.phase
        wf_model.phase = body.phase
        if body.phase not in wf_model.phases:
            wf_model.phases.append(body.phase)
        # Auto-archive open feedback from the previous phase on phase advance
        if old_phase and old_phase != body.phase and project_id and archived_by:
            try:
                from ..feedback_ledger import archive_phase_feedback
                archive_phase_feedback(project_id, old_phase, archived_by=archived_by)
            except Exception:
                pass  # best-effort; never block phase advance


async def _import_uploaded_file(
    file: UploadFile, project_id: str, project_user: str | None
) -> None:
    """Import an uploaded file as a document for the given project."""
    content = await file.read()
    import_document(
        file.filename or "uploaded_document",
        content,
        project=project_id,
        user=project_user,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/projects")
async def list_projects_endpoint(
    user: str | None = None,
    x_user: str | None = Header(None),
    skip: int = Query(0, ge=0, description="Number of projects to skip"),
    limit: int = Query(20, ge=1, le=200, description="Maximum projects to return"),
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """Return projects optionally filtered by user, with pagination.

    Response shape: ``{ items: [...], total: N, skip: 0, limit: 20 }``
    """
    from ..pagination import PaginatedResponse

    requested_user = (user or x_user) or None
    if requested_user:
        effective_user = _resolve_requested_user(requested_user, current_user)
    else:
        effective_user = None if _is_admin_user(current_user) else current_user.username
    cache_key = f"projects-{effective_user or 'all'}"
    cached = cache_get(cache_key)
    projects_list: list[ProjectModel]
    if cached:
        try:
            if isinstance(cached, bytes):
                cached = cached.decode()
            data = json.loads(cached)
            projects_list = [ProjectModel.model_validate(p) for p in data]
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            log_event("cache_decode_failed", key=cache_key, message=str(exc))
            projects_list = list_projects(effective_user)
    else:
        projects_list = list_projects(effective_user)
        cache_set(
            cache_key,
            json.dumps([p.model_dump(mode="json") for p in projects_list]),
            ttl=30,
        )
    page = PaginatedResponse.from_sequence(projects_list, skip=skip, limit=limit)
    return {
        "items": [p.model_dump(mode="json") if hasattr(p, "model_dump") else p for p in page.items],
        "total": page.total,
        "skip": page.skip,
        "limit": page.limit,
    }


@router.get("/projects/assigned/{username}", response_model=list[ProjectModel])
async def get_user_assignments_endpoint(
    username: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[ProjectModel]:
    """Get all projects assigned to a specific user through any mechanism."""
    return list_projects(_resolve_requested_user(username, current_user))


@router.post("/projects", status_code=201, response_model=ProjectModel)
async def create_project_endpoint(
    body: ProjectCreate,
    current_user: auth.User = Depends(auth.get_current_user),
) -> ProjectModel:  # noqa: C901
    """Create a new project."""
    if body.user is not None or not _is_admin_user(current_user):
        body.user = _resolve_requested_user(body.user, current_user)

    # Auto-assign the creator's org when no org_id is explicitly given
    if body.org_id is None:
        body.org_id = _get_user_org_id(current_user.username)

    if body.id is None or (isinstance(body.id, str) and not body.id.strip()):
        from ..search import search_index
        body.id = search_index.generate_project_id()
    else:
        existing = get_project(body.id)
        if existing is not None:
            raise HTTPException(status_code=409, detail="Project already exists")

    if body.document_number is None or (
        isinstance(body.document_number, str) and not body.document_number.strip()
    ):
        body.document_number = body.id

    project = ProjectModel(**body.model_dump())

    if body.workflow:
        template_requested = body.workflow in workflow_templates
        existing_workflow = workflows.get(body.workflow)
        if existing_workflow is not None and not template_requested:
            if existing_workflow.project and existing_workflow.project != project.id:
                raise HTTPException(
                    status_code=409,
                    detail="Workflow already assigned to another project",
                )
            existing_workflow.project = project.id
            project.workflow = existing_workflow.id
            project.initial_phase = existing_workflow.phase
            add_project(project)
            clear_cache()
            log_event(
                "create_project",
                user_id=project.user,
                project=project.id,
                message=render(
                    "create_project", user=project.user or "", project_id=project.id
                ),
            )
            _emit_webhook("project.created", {"project_id": project.id, "user": project.user})
            return project

        phases = _resolve_project_phases(body.doc_type, body.phase)
        template_name = _resolve_workflow_template(body.workflow, body.doc_type, body.phase)
        workflow = create_workflow(project.id, phases, template=template_name)
        project.workflow = workflow.id
        project.initial_phase = workflow.phase

    if body.phase and not body.workflow:
        project.initial_phase = body.phase

    add_project(project)
    clear_cache()
    log_event(
        "create_project",
        user_id=project.user,
        project=project.id,
        message=render("create_project", user=project.user or "", project_id=project.id),
    )
    _emit_webhook("project.created", {"project_id": project.id, "user": project.user})
    return project


@router.get("/projects/{project_id}", response_model=ProjectModel)
async def get_project_endpoint(
    project_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> ProjectModel:
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    _enforce_project_access(project, current_user)
    return project


@router.get("/projects/{project_id}/reviewers", response_model=list[str])
async def list_project_reviewers(
    project_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[str]:
    """Return reviewers assigned to a project."""
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    _enforce_project_access(project, current_user)
    return list(project.reviewers)


@router.post("/projects/{project_id}/reviewers", response_model=list[str])
async def add_project_reviewer_endpoint(
    project_id: str,
    body: ProjectReviewerPayload,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[str]:
    """Add a reviewer to a project."""
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    _enforce_project_manage_access(project, current_user)
    reviewer = body.reviewer.strip()
    if not reviewer:
        raise HTTPException(status_code=400, detail="Reviewer required")
    _ensure_reviewer_exists(reviewer)
    try:
        project = add_project_reviewer(project_id, reviewer)
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")
    return list(project.reviewers)


@router.put("/projects/{project_id}/reviewers/{reviewer}", response_model=list[str])
async def update_project_reviewer_endpoint(
    project_id: str,
    reviewer: str,
    body: ProjectReviewerPayload,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[str]:
    """Update a reviewer assignment for a project."""
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    _enforce_project_manage_access(project, current_user)
    new_reviewer = body.reviewer.strip()
    if not new_reviewer:
        raise HTTPException(status_code=400, detail="Reviewer required")
    _ensure_reviewer_exists(new_reviewer)
    try:
        project = update_project_reviewer(project_id, reviewer, new_reviewer)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return list(project.reviewers)


@router.delete("/projects/{project_id}/reviewers/{reviewer}", response_model=list[str])
async def remove_project_reviewer_endpoint(
    project_id: str,
    reviewer: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[str]:
    """Remove a reviewer from a project."""
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    _enforce_project_manage_access(project, current_user)
    try:
        project = remove_project_reviewer(project_id, reviewer)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return list(project.reviewers)


@router.get("/projects/{project_id}/reviews", response_model=list[ReviewModel])
async def list_project_reviews(
    project_id: str,
    phase: str | None = None,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[ReviewModel]:
    """Return reviews for a project."""
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    _enforce_project_access(project, current_user)
    return list_reviews(project_id, phase)


@router.post("/projects/{project_id}/reviews", response_model=ReviewModel, status_code=201)
async def create_project_review(
    project_id: str,
    body: ReviewCreate,
    x_user: str | None = Header(None),
    current_user: auth.User = Depends(auth.get_current_user),
) -> ReviewModel:
    """Create a new review entry for a project."""
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    _enforce_project_access(project, current_user)
    reviewer = _resolve_requested_user(x_user, current_user)

    review_data = {
        "id": str(uuid.uuid4()),
        "project_id": project_id,
        "reviewer": reviewer,
        "status": body.status,
        "comment": body.comment,
        "phase_id": body.phase_id,
        "required": body.required,
    }
    review = ReviewModel(**review_data)
    add_review(review)
    return review


@router.put("/projects/{project_id}", response_model=ProjectModel)
async def update_project_endpoint(  # noqa: C901
    project_id: str,
    request: Request,
    name: str | None = Form(None),
    user: str | None = Form(None),
    doc_type: str | None = Form(None),
    workflow: str | None = Form(None),
    title: str | None = Form(None),
    description: str | None = Form(None),
    sme: str | None = Form(None),
    docType: str | None = Form(None),
    file: UploadFile | None = File(default=None),
    current_user: auth.User = Depends(auth.get_current_user),
) -> ProjectModel:
    """Update project fields like name, user, doc_type, or workflow."""
    try:
        existing_project = get_project(project_id)
        if existing_project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        _enforce_project_manage_access(existing_project, current_user)
        previous_workflow_id = existing_project.workflow
        body, workflow_provided = await _parse_update_body(request)

        nara_schedule_number: str | None = None
        nara_disposition_authority: str | None = None
        nara_retention_period: str | None = None
        nara_record_series: str | None = None

        if body:
            if body.name is not None:
                name = body.name
            if body.user is not None:
                user = body.user
            if body.doc_type is not None:
                doc_type = body.doc_type
            if body.workflow is not None:
                workflow = body.workflow
            if body.description is not None:
                description = body.description
            if body.nara_schedule_number is not None:
                nara_schedule_number = body.nara_schedule_number
            if body.nara_disposition_authority is not None:
                nara_disposition_authority = body.nara_disposition_authority
            if body.nara_retention_period is not None:
                nara_retention_period = body.nara_retention_period
            if body.nara_record_series is not None:
                nara_record_series = body.nara_record_series

        if isinstance(workflow, str) and not workflow.strip():
            workflow = None

        requested_project_user = user or sme
        if requested_project_user is not None or not _is_admin_user(current_user):
            project_user = _resolve_requested_user(requested_project_user, current_user)
        else:
            project_user = requested_project_user
        project_doc_type = doc_type or docType or existing_project.doc_type
        project_description = description

        workflow_id, workflow_set = _resolve_workflow(
            request,
            workflow_provided,
            workflow,
            body,
            project_id,
            project_doc_type,
            existing_project.workflow,
        )

        initial_phase = None
        if body and body.phase is not None and workflow_id is None:
            initial_phase = body.phase

        updated_project = update_project(
            project_id,
            name=name or title,
            user=project_user,
            doc_type=project_doc_type,
            workflow=workflow_id,
            workflow_set=workflow_set,
            description=project_description,
            initial_phase=initial_phase,
            nara_schedule_number=nara_schedule_number,
            nara_disposition_authority=nara_disposition_authority,
            nara_retention_period=nara_retention_period,
            nara_record_series=nara_record_series,
        )

        if (
            workflow_set
            and previous_workflow_id
            and previous_workflow_id != updated_project.workflow
        ):
            previous_workflow = workflows.get(previous_workflow_id)
            if previous_workflow and previous_workflow.project == project_id:
                previous_workflow.project = ""

        _update_workflow_phase(
            request, body, updated_project,
            project_id=project_id,
            archived_by=current_user.username,
        )

        if file:
            await _import_uploaded_file(file, project_id, project_user)

        clear_cache()
        return updated_project
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete("/projects/{project_id}", response_model=ProjectModel)
async def delete_project_endpoint(
    project_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> ProjectModel:
    """Delete a project and its persisted record."""
    existing_project = get_project(project_id)
    if existing_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    _enforce_project_manage_access(existing_project, current_user)
    try:
        removed = remove_project(project_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found") from None
    clear_cache()
    log_event(
        "delete_project",
        user_id=removed.user,
        project=removed.id,
        message=render("delete_project", user=removed.user or "", project_id=removed.id),
    )
    return removed


@router.get("/projects/{project_id}/workflow", response_model=WorkflowModel)
async def get_project_workflow_endpoint(
    project_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> WorkflowModel:
    """Return the workflow associated with a project."""
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    _enforce_project_access(project, current_user)
    for wf in workflows.values():
        if wf.project == project_id:
            return wf
    raise HTTPException(status_code=404, detail="Workflow not found")


@router.put("/projects/{project_id}/priority", response_model=ProjectModel)
async def update_priority_endpoint(
    project_id: str,
    body: PriorityUpdate,
    current_user: auth.User = Depends(auth.get_current_user),
) -> ProjectModel:
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    _enforce_project_manage_access(project, current_user)
    try:
        return set_project_priority(project_id, body.priority)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/projects/{project_id}/temporary", response_model=ProjectModel)
async def temporary_assign_endpoint(
    project_id: str,
    body: TemporaryAssign,
    current_user: auth.User = Depends(auth.get_current_user),
) -> ProjectModel:
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    _enforce_project_manage_access(project, current_user)
    assigned_user = _resolve_requested_user(body.user, current_user)
    try:
        return assign_temporary(project_id, assigned_user, body.until)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/projects/{project_id}/preferences", response_model=ProjectPreferences)
async def get_project_preferences_endpoint(
    project_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> ProjectPreferences:
    """Return editor extension preferences for a project."""
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    _enforce_project_access(project, current_user)
    return get_project_preferences(project_id)


@router.put("/projects/{project_id}/preferences", response_model=ProjectPreferences)
async def update_project_preferences_endpoint(
    project_id: str,
    body: ProjectPreferences,
    current_user: auth.User = Depends(auth.get_current_user),
) -> ProjectPreferences:
    """Update editor extension preferences for a project."""
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    _enforce_project_manage_access(project, current_user)
    return update_project_preferences(project_id, body.model_dump())


@router.get("/projects/{project_id}/approvals/pdf")
async def project_approvals_pdf_endpoint(
    project_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> Response:
    """Return merged approval PDFs for a project."""
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    _enforce_project_access(project, current_user)
    try:
        data = build_approvals_summary_pdf(project_id, actor=current_user.username)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    log_event(
        "approval_summary_downloaded",
        user_id=current_user.username,
        project=project_id,
    )
    log_audit_event(
        project_id,
        "approval_summary_downloaded",
        actor=current_user.username,
        project=project_id,
    )
    return Response(
        data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="approvals-{project_id}.pdf"'},
    )


# ---------------------------------------------------------------------------
# Per-document quality scores
# ---------------------------------------------------------------------------

class DocumentScore(BaseModel):
    """Quality metrics for a single document."""

    document_id: str
    quality_score: float
    plain_language_grade: str
    flesch_reading_ease: float
    quality_flags: dict[str, float]
    high_risk_terms: list[str]
    doc_type_avg_score: float | None = None
    score_history: list[dict] = []  # Item 35: last 5 historical scores


@router.get(
    "/projects/{project_id}/documents/scores",
    response_model=list[DocumentScore],
)
async def get_project_document_scores(
    project_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[DocumentScore]:
    """Return per-document quality metrics for every document in a project."""
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    _enforce_project_access(project, current_user)

    project_docs = [
        d for d in list_documents() if d.project == project_id
    ]
    if not project_docs:
        return []

    # Pre-compute quality assessments so we can derive per-type averages.
    assessments: list[tuple[DocumentModel, QualityAssessment]] = []
    for doc in project_docs:
        qa = quality_assessment(doc.content)
        assessments.append((doc, qa))

    # Build per-doc_type average scores across *all* documents (not just
    # this project) so each document can be compared against its type.
    all_docs = list_documents()
    type_scores: dict[str | None, list[float]] = {}
    for d in all_docs:
        dt = d.project and get_project(d.project)
        doc_type = dt.doc_type if dt else None
        qa = quality_assessment(d.content)
        type_scores.setdefault(doc_type, []).append(qa.score)

    project_doc_type = project.doc_type

    # Item 35: fetch score history for all project docs in one DB pass.
    def _get_score_history(doc_id: str) -> list[dict]:
        """Return last 5 quality score history entries for a document."""
        try:
            from sqlalchemy import desc as _desc
            from sqlalchemy import select as _select

            from ..db_store import get_db
            from ..models import DocumentQualityScore as _OrmScore

            db = get_db()
            with db.orm_session() as session:
                rows = (
                    session.execute(
                        _select(_OrmScore)
                        .where(_OrmScore.document_id == doc_id)
                        .order_by(_desc(_OrmScore.scored_at))
                        .limit(5)
                    )
                    .scalars()
                    .all()
                )
                return [
                    {"date": r.scored_at.isoformat(), "score": r.quality_score}
                    for r in rows
                ]
        except Exception:
            return []

    results: list[DocumentScore] = []
    for doc, qa in assessments:
        pl = score_plain_language(doc.content)
        flags = dict(zip(QUALITY_FLAG_NAMES, qa.flags))
        risky = high_risk_warnings(doc.content)

        avg_scores = type_scores.get(project_doc_type)
        avg: float | None = None
        if avg_scores:
            avg = round(sum(avg_scores) / len(avg_scores), 4)

        history = _get_score_history(doc.id)

        results.append(
            DocumentScore(
                document_id=doc.id,
                quality_score=round(qa.score, 4),
                plain_language_grade=pl.grade_level,
                flesch_reading_ease=pl.flesch_reading_ease,
                quality_flags=flags,
                high_risk_terms=risky,
                doc_type_avg_score=avg,
                score_history=history,
            )
        )

    return results


# ---------------------------------------------------------------------------
# NARA metadata endpoint (Item 44 Phase 7)
# ---------------------------------------------------------------------------

class NaraMetadataResponse(BaseModel):
    """NARA records management fields for a project."""

    project_id: str
    nara_schedule_number: str | None = None
    nara_disposition_authority: str | None = None
    nara_retention_period: str | None = None
    nara_record_series: str | None = None


@router.get(
    "/projects/{project_id}/nara-metadata",
    response_model=NaraMetadataResponse,
)
async def get_project_nara_metadata(
    project_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> NaraMetadataResponse:
    """Return NARA records management metadata for a project."""
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    _enforce_project_access(project, current_user)
    return NaraMetadataResponse(
        project_id=project_id,
        nara_schedule_number=project.nara_schedule_number,
        nara_disposition_authority=project.nara_disposition_authority,
        nara_retention_period=project.nara_retention_period,
        nara_record_series=project.nara_record_series,
    )

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
from pydantic import BaseModel, Field, field_validator

from .. import auth
from ..cache import cache_get, cache_set, clear_cache
from ..rbac import has_role


def _emit_webhook(event: str, data: dict) -> None:
    """Best-effort lifecycle webhook emission — never raises."""
    try:
        from .webhooks import emit_lifecycle_event
        emit_lifecycle_event(event, data)  # type: ignore[arg-type]
    except Exception as exc:
        _logger.error("lifecycle webhook emission failed for event %r: %s", event, exc, exc_info=exc)
from ..approvals import build_approvals_summary_pdf
from ..audit import log_audit_event
from ..doc_types import get_document_type
from ..doc_validation import score_plain_language
from ..documents import DocumentModel, create_blank_document, import_document, list_documents
from ..logs import log_event
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


def _project_display(project: ProjectModel) -> str:
    """Return a compact project label suitable for busy audit feeds."""
    doc_number = (project.document_number or project.id or "").strip()
    if doc_number and doc_number != project.id:
        return f"'{project.name}' ({doc_number}; id {project.id})"
    return f"'{project.name}' (id {project.id})"


def _log_project_activity(
    action: str,
    project: ProjectModel,
    *,
    actor: str,
    message: str,
    **details: object,
) -> None:
    """Write a project-scoped audit event with consistent identifying context."""
    context = {
        "project": project.id,
        "project_id": project.id,
        "project_name": project.name,
        "document_number": project.document_number,
        "owner": project.user,
        "phase": project.initial_phase,
        "workflow": project.workflow,
        "message": message,
    }
    context.update(details)
    log_event(
        action,
        user_id=actor,
        entity_id=project.id,
        entity_type="project",
        **context,
    )


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ProjectCreate(BaseModel):
    """Input model for creating projects."""

    id: str | None = Field(default=None, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    document_number: str | None = Field(default=None, max_length=100)
    user: str | None = Field(default=None, max_length=150)
    # Optional organization scoping — if omitted the creator's org is used.
    org_id: int | None = Field(default=None, ge=1)
    doc_type: str | None = Field(default=None, max_length=100)
    phase: str | None = Field(default=None, max_length=100)
    workflow: str | None = Field(default=None, max_length=200)
    priority: int = Field(default=0, ge=0, le=4)
    description: str | None = Field(default=None, max_length=2000)
    # NARA records management fields
    nara_schedule_number: str | None = Field(default=None, max_length=100)
    nara_disposition_authority: str | None = Field(default=None, max_length=200)
    nara_retention_period: str | None = Field(default=None, max_length=100)
    nara_record_series: str | None = Field(default=None, max_length=200)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be blank")
        return v


class ProjectUpdate(BaseModel):
    """Fields allowed when updating a project."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    user: str | None = Field(default=None, max_length=150)
    doc_type: str | None = Field(default=None, max_length=100)
    phase: str | None = Field(default=None, max_length=100)
    workflow: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    # NARA records management fields
    nara_schedule_number: str | None = Field(default=None, max_length=100)
    nara_disposition_authority: str | None = Field(default=None, max_length=200)
    nara_retention_period: str | None = Field(default=None, max_length=100)
    nara_record_series: str | None = Field(default=None, max_length=200)


class ProjectReviewerPayload(BaseModel):
    """Input model for managing project reviewers."""

    reviewer: str = Field(min_length=1, max_length=150)


class PriorityUpdate(BaseModel):
    """Input for updating project priority."""

    priority: int = Field(ge=0, le=4)


class TemporaryAssign(BaseModel):
    """Input for temporary reassignment."""

    user: str = Field(min_length=1, max_length=150)
    until: datetime


class WatchBody(BaseModel):
    user: str = Field(min_length=1, max_length=150)


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
        # Emit a specific phase_transitioned audit event so dashboards can
        # track progress without navigating into each project.
        if old_phase != body.phase and project_id and archived_by:
            try:
                _log_project_activity(
                    "phase_transitioned",
                    updated_project,
                    actor=archived_by,
                    message=(
                        f"{archived_by} advanced project {_project_display(updated_project)} "
                        f"from phase '{old_phase or 'none'}' to '{body.phase}'"
                    ),
                    old_phase=old_phase,
                    new_phase=body.phase,
                )
            except Exception:
                pass  # best-effort; never block phase advance
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

    user_org_id = _get_user_org_id(current_user.username)
    # Auto-assign the creator's org when no org_id is explicitly given.
    # Non-admins may not choose another tenant's organization ID.
    if body.org_id is None:
        body.org_id = user_org_id
    elif not _is_admin_user(current_user) and body.org_id != user_org_id:
        raise HTTPException(status_code=403, detail="Forbidden")

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
            create_blank_document(
                project=project.id,
                user=project.user,
                title=project.name or "Untitled Document",
            )
            clear_cache()
            _log_project_activity(
                "create_project",
                project,
                actor=current_user.username,
                message=(
                    f"{current_user.username} created project {_project_display(project)} "
                    f"for owner {project.user or 'unassigned'} in phase "
                    f"{project.initial_phase or 'not set'}"
                ),
                owner=project.user,
                created_by=current_user.username,
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
    create_blank_document(
        project=project.id,
        user=project.user,
        title=project.name or "Untitled Document",
    )
    clear_cache()
    _log_project_activity(
        "create_project",
        project,
        actor=current_user.username,
        message=(
            f"{current_user.username} created project {_project_display(project)} "
            f"for owner {project.user or 'unassigned'} in phase "
            f"{project.initial_phase or 'not set'}"
        ),
        owner=project.user,
        created_by=current_user.username,
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
    _log_project_activity(
        "reviewer_added",
        project,
        actor=current_user.username,
        message=(
            f"{current_user.username} added reviewer {reviewer} to project "
            f"{_project_display(project)}"
        ),
        reviewer=reviewer,
    )
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
    _log_project_activity(
        "reviewer_updated",
        project,
        actor=current_user.username,
        message=(
            f"{current_user.username} changed reviewer {reviewer} to {new_reviewer} "
            f"on project {_project_display(project)}"
        ),
        old_reviewer=reviewer,
        reviewer=new_reviewer,
    )
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
    _log_project_activity(
        "reviewer_removed",
        project,
        actor=current_user.username,
        message=(
            f"{current_user.username} removed reviewer {reviewer} from project "
            f"{_project_display(project)}"
        ),
        reviewer=reviewer,
    )
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
    _log_project_activity(
        "review_submitted",
        project,
        actor=reviewer,
        message=(
            f"{reviewer} submitted {body.status} review for project "
            f"{_project_display(project)}"
        ),
        reviewer=reviewer,
        review_id=review.id,
        review_status=body.status,
        phase_id=body.phase_id,
    )
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
        previous_name = existing_project.name
        previous_owner = existing_project.user
        previous_doc_type = existing_project.doc_type
        previous_phase = existing_project.initial_phase
        previous_workflow_id = existing_project.workflow
        previous_nara_schedule = existing_project.nara_schedule_number
        previous_nara_disposition = existing_project.nara_disposition_authority
        previous_nara_retention = existing_project.nara_retention_period
        previous_nara_series = existing_project.nara_record_series
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
        changed_fields: dict[str, dict[str, str | None]] = {}
        comparisons = {
            "name": (previous_name, updated_project.name),
            "owner": (previous_owner, updated_project.user),
            "document_type": (previous_doc_type, updated_project.doc_type),
            "phase": (previous_phase, updated_project.initial_phase),
            "workflow": (previous_workflow_id, updated_project.workflow),
            "nara_schedule_number": (previous_nara_schedule, updated_project.nara_schedule_number),
            "nara_disposition_authority": (previous_nara_disposition, updated_project.nara_disposition_authority),
            "nara_retention_period": (previous_nara_retention, updated_project.nara_retention_period),
            "nara_record_series": (previous_nara_series, updated_project.nara_record_series),
        }
        for field, (before, after) in comparisons.items():
            if before != after:
                changed_fields[field] = {"from": before, "to": after}
        if file:
            changed_fields["document_upload"] = {
                "from": None,
                "to": file.filename or "uploaded_document",
            }
        if changed_fields:
            changed_names = ", ".join(sorted(changed_fields))
            _log_project_activity(
                "update_project",
                updated_project,
                actor=current_user.username,
                message=(
                    f"{current_user.username} updated {changed_names} on project "
                    f"{_project_display(updated_project)}"
                ),
                changed_fields=changed_fields,
            )
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
    _log_project_activity(
        "delete_project",
        removed,
        actor=current_user.username,
        message=(
            f"{current_user.username} deleted project {_project_display(removed)} "
            f"owned by {removed.user or 'unassigned'}"
        ),
        deleted_owner=removed.user,
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
    previous_priority = project.priority
    try:
        updated = set_project_priority(project_id, body.priority)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    _log_project_activity(
        "project_priority_updated",
        updated,
        actor=current_user.username,
        message=(
            f"{current_user.username} changed priority for project "
            f"{_project_display(updated)} from {previous_priority} to {body.priority}"
        ),
        previous_priority=previous_priority,
        priority=body.priority,
    )
    return updated


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
        updated = assign_temporary(project_id, assigned_user, body.until)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    _log_project_activity(
        "project_temporary_assigned",
        updated,
        actor=current_user.username,
        message=(
            f"{current_user.username} temporarily assigned project "
            f"{_project_display(updated)} to {assigned_user} until {body.until.isoformat()}"
        ),
        temporary_user=assigned_user,
        temporary_until=body.until.isoformat(),
    )
    return updated


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
    updated = update_project_preferences(project_id, body.model_dump())
    _log_project_activity(
        "project_preferences_updated",
        project,
        actor=current_user.username,
        message=(
            f"{current_user.username} updated editor preferences for project "
            f"{_project_display(project)}"
        ),
    )
    return updated


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

    def _is_blank_document(content: str) -> bool:
        """Return True when the document contains only the initial blank template.

        The blank template is <h1>{title}</h1><p></p>.  We detect this by
        checking that after stripping all HTML the remaining content is only
        a single block of text with no body paragraphs (no second <p> or <li>).
        """
        import re as _re
        raw = content or ""
        # Check for the exact pattern produced by create_blank_document:
        # one heading tag followed only by empty block tags.
        no_heading = _re.sub(r"<h[1-6][^>]*>.*?</h[1-6]>", "", raw, flags=_re.IGNORECASE | _re.DOTALL)
        remaining = _re.sub(r"<[^>]+>", "", no_heading).strip()
        if not remaining:
            return True
        # Fallback: very short stripped content (< 20 chars) is also blank.
        stripped = _re.sub(r"<[^>]+>", "", raw).strip()
        return len(stripped) < 20

    # Pre-compute quality assessments so we can derive per-type averages.
    # Skip documents that are still blank (just created, no real content yet).
    assessments: list[tuple[DocumentModel, QualityAssessment]] = []
    for doc in project_docs:
        if _is_blank_document(doc.content):
            continue
        qa = quality_assessment(doc.content)
        assessments.append((doc, qa))

    if not assessments:
        return []

    # Build per-doc_type average scores across *all* documents (not just
    # this project) so each document can be compared against its type.
    # Skip blank documents to avoid skewing the average.
    all_docs = list_documents()
    type_scores: dict[str | None, list[float]] = {}
    for d in all_docs:
        if _is_blank_document(d.content):
            continue
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

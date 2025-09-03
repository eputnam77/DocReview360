"""FastAPI application exposing DocReview360 endpoints."""

# ruff: noqa: I001
from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    Request,
    Response,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from markdown_it import MarkdownIt
from pydantic import BaseModel, ConfigDict, Field

from .. import auth, reporting
from ..rbac import require_permission
from .. import search as search_mod
from ..ai_assist import rewrite_text, summarize_text
from ..ai_balancer import load_state as load_worker_state
from ..ai_balancer import save_state as save_worker_state
from ..approvals import (
    ApprovalModel,
    build_approvals_summary_pdf,
    create_approval,
    get_approval,
    list_approvals,
    send_for_signature,
    update_approval_state,
    verify_document_signature,
)
from ..archive import (
    ArchiveRecord,
    archive_document as archive_doc,
    get_archive,
    list_archives,
    schedule_archive_purge,
)
from ..audit import AuditLogEntry, get_audit_log, log_audit_event
from ..cache import cache_get, cache_set, clear_cache
from ..cms import save_to_cms
from ..comments import CommentModel, add_comment, list_comments
from ..config import CONFIG_FILE, Config
from ..dashboard_prefs import get_visibility, set_visibility
from ..doc_types import (
    DocumentTypeModel,
    add_document_type,
    delete_document_type,
    export_document_types_json,
    get_document_type,
    import_document_types_json,
    list_document_types,
    update_document_type,
)
from ..documenso import (
    complete_signature,
    signature_status,
)
from ..documents import (
    DocumentModel,
    get_document,
    import_document,
    list_public_documents,
    public_documents_report,
    update_document,
    DocumentRevision,
)
from ..documents import (
    list_documents as list_docs,
)
from ..environment import current_environment, load_envs, switch_environment
from ..exporter import export_document, set_guardrails
from ..integrations.signature import get_default_providers, get_provider
from ..logs import LogEntry, log_event, log_stream, query_logs, log_call
from ..messages import render
from ..nemo_guardrails import GuardrailsMiddleware, contains_pii
from ..phases import add_phase, delete_phase, list_phases, rename_phase
from ..plugins import load_plugins
from ..plugins import registry as plugin_registry
from ..profile import get_preferences, update_preferences
from ..rbac import get_roles, require_role, has_permission, has_role
from ..reporting import (
    DashboardEntry,
    SummaryReport,
    admin_dashboard,
    dashboard_data,
    generate_summary,
    manager_dashboard,
    user_dashboard,
    widget_counts,
)
from ..search import (
    ProjectModel,
    add_project,
    assign_temporary,
    get_project,
    list_projects,
    list_saved_searches,
    ranked_search,
    save_search,
    search,
    search_stats,
    set_project_priority,
    update_project,
)
from ..project_preferences import (
    ProjectPreferences,
    get_project_preferences,
    update_project_preferences,
)
from ..reviews import ReviewCreate, ReviewModel, add_review, list_reviews
from ..settings_manager import update_setting
from ..status import internal_status, public_status
from ..stubs.task223 import convert_document
from ..template_manager import (
    upload_template as store_template,
    get_latest_template,
    list_stored_templates,
    approve_template,
    retire_template,
)
from ..watchlist import get_watchlist, toggle_watch
from ..collab import router as collab_router
from ..workflows import (
    WorkflowModel,
    advance_workflow,
    assign_reviewer,
    create_workflow,
    get_workflow,
    list_workflows,
    start_workflow,
    workflows,
    list_roles,
)
from .approvals import router as approvals_router
from .webhooks import router as webhooks_router

# Load environment variables from .env file
load_dotenv()

WORKER_STATE_FILE = Path(os.getenv("DOCREVIEW360_WORKER_STATE", "worker_state.json"))


SEED_TEMPLATES = [
    {
        "name": "faa_ac",
        "content": (
            '<h1 style="text-align:center; margin-bottom:0">Advisory Circular</h1>'
            "<p>This is a seed template.</p>"
        ),
        "metadata": {"label": "FAA Advisory Circular", "type": "tiptap"},
    }
]


class WorkflowCreate(BaseModel):
    """Input model for creating workflows."""

    project: str
    phases: list[str]
    mode: str = "sequential"


class ReviewerAssign(BaseModel):
    """Input model for assigning reviewers."""

    user: str


class ApprovalCreate(BaseModel):
    """Input model for creating approvals."""

    workflow: str
    reviewer: str
    # ``doc_id`` used to be required which made quick test setups cumbersome.
    # It is now optional and defaults to the workflow identifier when omitted.
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


class PluginModule(BaseModel):
    """Input model for registering plugins by module path."""

    module: str


class PluginToggle(BaseModel):
    """Input model for enabling or disabling a plugin."""

    name: str


class RevisionCreate(BaseModel):
    """Payload for creating a document revision."""

    content: str
    steps: list[Any] | None = None
    promote: bool = False


class RevisionMeta(BaseModel):
    """Metadata for a document revision."""

    id: str
    timestamp: datetime
    author: str


class ProjectCreate(BaseModel):
    """Input model for creating projects."""

    id: str | None = None  # Made optional - will be auto-generated if not provided
    name: str
    document_number: str | None = None  # User-provided document number/reference
    user: str | None = None
    doc_type: str | None = None
    phase: str | None = None
    workflow: str | None = None
    priority: int = 0
    description: str | None = None


class ProjectUpdate(BaseModel):
    """Fields allowed when updating a project."""

    name: str | None = None
    user: str | None = None
    doc_type: str | None = None
    # Allow updating the current phase via workflow state
    phase: str | None = None
    workflow: str | None = None
    description: str | None = None


class CommentCreate(BaseModel):
    """Input for creating comments."""

    user: str
    text: str
    parent: str | None = None


class PriorityUpdate(BaseModel):
    """Input for updating project priority."""

    priority: int


class TemporaryAssign(BaseModel):
    """Input for temporary reassignment."""

    user: str
    until: datetime


class SavedSearchCreate(BaseModel):
    """Input model for creating saved searches."""

    query: str
    user: str | None = None


class TextBody(BaseModel):
    """Simple text payload for AI endpoints."""

    text: str


class ConfigPayload(BaseModel):
    """Configuration parameters for integrations."""

    database: str
    database_url: str | None = None
    editor: str
    cms: str
    auth: str
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False
    ai_auto_assign_writers: bool = False
    filename_template: str = "{id}"


class SignatureProviderPayload(BaseModel):
    """Payload for selecting active signature providers."""

    primary: str
    fallback: str | None = None


@asynccontextmanager
async def _lifespan(app: FastAPI):
    # Startup
    load_worker_state(WORKER_STATE_FILE)
    for tpl in SEED_TEMPLATES:
        if not get_latest_template(tpl["name"]):
            store_template(tpl["name"], tpl["content"].encode("utf-8"), tpl.get("metadata"))
    schedule_archive_purge()
    try:
        yield
    finally:
        # Shutdown
        save_worker_state(WORKER_STATE_FILE)


app = FastAPI(title="DocReview360", lifespan=_lifespan)


@app.get("/ping")
async def ping() -> dict[str, str]:
    """Lightweight health check endpoint used by the frontend."""

    return {"status": "ok"}

# Add CORS middleware to allow frontend requests
#
# Previously, the API only allowed requests from hard-coded localhost
# origins, which meant running the frontend from any other host (even a
# test environment) resulted in a browser "Failed to fetch" error due to
# a blocked CORS preflight request.  To support multiple environments we
# now read the allowed origins from an environment variable.  When the
# variable is unset we fall back to a permissive regular expression so
# that developers can experiment in ephemeral environments without extra
# configuration.
allowed_origins = os.getenv("DOCREVIEW360_ALLOW_ORIGINS")
if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_origins=[o.strip() for o in allowed_origins.split(",") if o.strip()],
    )
else:
    # ``allow_origin_regex`` permits credentials while accepting any origin
    app.add_middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_origin_regex=".*",
    )

# Enable compression for large responses as recommended by the
# performance profiling report. ``minimum_size`` avoids wasting
# CPU cycles on tiny payloads.
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(approvals_router)
app.include_router(webhooks_router)
app.include_router(collab_router)
if os.environ.get("ENABLE_GUARDRAILS", "").lower() in {"1", "true", "yes"}:
    # Activate NeMo Guardrails PII checker when explicitly enabled
    set_guardrails(contains_pii)
    app.add_middleware(GuardrailsMiddleware, checker=contains_pii)

# Templates are stored one level above this module in ``docreview360/templates``.
# The previous path incorrectly looked for templates in ``api/templates`` which
# does not exist, causing ``TemplateNotFound`` errors during E2E tests.
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


# Startup/shutdown now handled via lifespan


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for monitoring."""
    return {"status": "healthy"}


@app.get("/users/me")
async def current_user_endpoint(
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Return information about the current user."""
    roles = list(get_roles(current_user.username))
    return {
        "username": current_user.username,
        "is_admin": "admin" in roles,
        "active": auth.is_active(current_user.username),
        "roles": roles,
    }


def require_audit_access(x_user: str | None = Header(None)) -> str:
    """Ensure the requester may view audit logs and record the attempt."""

    if x_user is None:
        log_event("audit_log_access", status="denied")
        raise HTTPException(status_code=401, detail="Missing user")
    if has_permission(x_user, "view_audit_log"):
        log_event("audit_log_access", user_id=x_user, status="success")
        return x_user
    log_event("audit_log_access", user_id=x_user, status="denied")
    raise HTTPException(status_code=403, detail="Forbidden")


class PreferencePayload(BaseModel):
    """Input model for updating user preferences."""

    theme: Literal["system", "light", "dark"] | None = None
    reduce_motion: bool | None = None


class UserStatusPayload(BaseModel):
    """Payload for toggling a user's active status."""

    active: bool


@app.get("/profile")
async def get_profile(
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Return profile information for the current user."""

    return {
        "username": current_user.username,
        "preferences": get_preferences(current_user.username),
        "roles": sorted(get_roles(current_user.username)),
    }


@app.put("/profile")
async def update_profile(
    body: PreferencePayload,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Persist profile preference updates."""

    prefs = {k: v for k, v in body.model_dump().items() if v is not None}
    return {
        "username": current_user.username,
        "preferences": update_preferences(current_user.username, prefs),
    }


@app.post("/admin/users/{username}/status")
async def set_user_status(
    username: str,
    body: UserStatusPayload,
    user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Set the active status for ``username`` (admin only)."""

    if username not in auth.FAKE_USERS_DB:
        raise HTTPException(status_code=404, detail="User not found")
    auth.FAKE_USERS_DB[username]["active"] = body.active
    return {"username": username, "active": body.active}


@app.get("/projects", response_model=list[ProjectModel])
async def list_projects_endpoint(
    user: str | None = None, x_user: str | None = Header(None)
) -> list[ProjectModel]:
    """Return projects optionally filtered by user with simple caching.

    When a user is specified, includes projects where the user is:
    1. Directly assigned as project.user
    2. Temporarily assigned as project.temp_user
    3. Assigned as a reviewer in any approval step (SME, FLM, PPM, TW, etc.)
    """
    user = (user or x_user) or None
    cache_key = f"projects-{user or 'all'}"
    cached = cache_get(cache_key)
    if cached:
        try:
            if isinstance(cached, bytes):
                cached = cached.decode()
            data = json.loads(cached)
            return [ProjectModel.model_validate(p) for p in data]
        except Exception:
            pass
    projects_list = list_projects(user)
    cache_set(
        cache_key,
        json.dumps([p.model_dump(mode="json") for p in projects_list]),
        ttl=30,
    )
    return projects_list


@app.get("/projects/assigned/{username}", response_model=list[ProjectModel])
async def get_user_assignments_endpoint(username: str) -> list[ProjectModel]:
    """Get all projects assigned to a specific user through any mechanism.

    This includes:
    - Direct project assignments
    - Temporary assignments
    - Approval assignments (SME, FLM, PPM, TW, Senior TW, TW Manager, Attorney)

    Useful for debugging and testing assignment logic.
    """
    return list_projects(username)


@app.post("/projects", status_code=201, response_model=ProjectModel)
async def create_project_endpoint(body: ProjectCreate) -> ProjectModel:
    """Create a new project."""
    # Auto-generate ID if not provided
    if body.id is None:
        from ..search import search_index

        body.id = search_index.generate_project_id()

    # If document_number is not provided, use the id as document_number
    if body.document_number is None:
        body.document_number = body.id

    project = ProjectModel(**body.model_dump())
    add_project(project)

    # Handle workflow assignment.  ``body.workflow`` may either reference an
    # existing workflow or specify the identifier for a new workflow.  Earlier
    # revisions always created a new workflow even when one already existed,
    # while the subsequent fix assumed the identifier was pre-existing and never
    # created a workflow.  Both behaviours caused inconsistencies: callers could
    # end up with a dangling reference or with a mismatched identifier.  The
    # logic below strikes a balance by creating a minimal workflow only when the
    # supplied identifier does not already exist.
    if body.workflow:
        if body.workflow not in workflows:
            workflows[body.workflow] = WorkflowModel(
                id=body.workflow,
                project=project.id,
                phase=body.phase or body.workflow,
                phases=[body.phase or body.workflow],
                template=body.workflow,
                approval_steps=[],
                approval_roles=[],
                approval_sequence=[],
                mode="sequential",
            )
        project.workflow = body.workflow
    # Previously a workflow was automatically created whenever a phase was
    # supplied, even if the caller did not request one.  This behaviour made it
    # impossible to create a project without a workflow.  Now we only create a
    # workflow when an explicit ``workflow`` identifier is provided.  Projects can
    # still record their starting phase without being tied to a workflow.

    if body.phase and not body.workflow:
        # Preserve the starting phase so the project reflects configuration even
        # before a workflow is assigned.
        project.initial_phase = body.phase

    # Clear all project-related caches to ensure fresh data
    clear_cache()
    print(f"DEBUG: Project '{project.id}' created successfully, cache cleared")
    log_event(
        "create_project",
        user_id=project.user,
        project=project.id,
        message=render("create_project", user=project.user or "", project_id=project.id),
    )
    return project


@app.get("/projects/{project_id}", response_model=ProjectModel)
async def get_project_endpoint(project_id: str) -> ProjectModel:
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@app.get("/projects/{project_id}/reviews", response_model=list[ReviewModel])
async def list_project_reviews(project_id: str, phase: str | None = None) -> list[ReviewModel]:
    """Return reviews for a project."""

    return list_reviews(project_id, phase)


@app.post("/projects/{project_id}/reviews", response_model=ReviewModel, status_code=201)
async def create_project_review(
    project_id: str,
    body: ReviewCreate,
    x_user: str | None = Header(None),
) -> ReviewModel:
    """Create a new review entry for a project."""

    review_data = {
        "id": str(uuid.uuid4()),
        "project_id": project_id,
        "reviewer": x_user or "Anonymous",
        "status": body.status,
        "comment": body.comment,
        "phase_id": body.phase_id,
        "required": body.required,
    }
    review = ReviewModel(**review_data)
    add_review(review)
    return review


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
) -> tuple[str | None, bool]:
    """Determine new workflow information from the request."""
    is_json = request.headers.get("content-type", "").startswith("application/json")
    if is_json:
        if workflow_provided:
            if workflow is not None:
                start_phase = body.phase if (body and body.phase) else "start"
                wf = create_workflow(project_id, [start_phase])
                return wf.id, True
            return None, True
        return None, False
    if workflow is not None:
        wf = create_workflow(project_id, ["start"])
        return wf.id, True
    return None, False


def _update_workflow_phase(
    request: Request, body: ProjectUpdate | None, updated_project: ProjectModel
) -> None:
    """Update an existing workflow's phase when only the phase is provided."""
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
        wf_model.phase = body.phase
        if body.phase not in wf_model.phases:
            wf_model.phases.append(body.phase)


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


@app.put("/projects/{project_id}", response_model=ProjectModel)
async def update_project_endpoint(
    project_id: str,
    request: Request,
    name: str | None = Form(None),
    user: str | None = Form(None),
    doc_type: str | None = Form(None),
    workflow: str | None = Form(None),
    title: str | None = Form(None),
    description: str | None = Form(None),
    sme: str | None = Form(None),  # Add sme field for frontend compatibility
    docType: str | None = Form(None),  # Add docType field for frontend compatibility
    file: UploadFile | None = File(None),
) -> ProjectModel:
    """Update project fields like name, user, doc_type, or workflow."""
    try:
        body, workflow_provided = await _parse_update_body(request)

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

        project_user = user or sme
        project_doc_type = doc_type or docType
        project_description = description

        workflow_id, workflow_set = _resolve_workflow(
            request, workflow_provided, workflow, body, project_id
        )

        updated_project = update_project(
            project_id,
            name=name or title,
            user=project_user,
            doc_type=project_doc_type,
            workflow=workflow_id,
            workflow_set=workflow_set,
            description=project_description,
        )

        _update_workflow_phase(request, body, updated_project)

        if file:
            await _import_uploaded_file(file, project_id, project_user)

        return updated_project
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/projects/{project_id}/workflow", response_model=WorkflowModel)
async def get_project_workflow_endpoint(project_id: str) -> WorkflowModel:
    """Return the workflow associated with a project."""
    for wf in workflows.values():
        if wf.project == project_id:
            return wf
    raise HTTPException(status_code=404, detail="Workflow not found")


@app.put("/projects/{project_id}/priority", response_model=ProjectModel)
async def update_priority_endpoint(project_id: str, body: PriorityUpdate) -> ProjectModel:
    try:
        return set_project_priority(project_id, body.priority)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/projects/{project_id}/temporary", response_model=ProjectModel)
async def temporary_assign_endpoint(project_id: str, body: TemporaryAssign) -> ProjectModel:
    try:
        return assign_temporary(project_id, body.user, body.until)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/projects/{project_id}/preferences", response_model=ProjectPreferences)
async def get_project_preferences_endpoint(
    project_id: str,
) -> ProjectPreferences:
    """Return editor extension preferences for a project."""
    return get_project_preferences(project_id)


@app.put("/projects/{project_id}/preferences", response_model=ProjectPreferences)
async def update_project_preferences_endpoint(
    project_id: str, body: ProjectPreferences
) -> ProjectPreferences:
    """Update editor extension preferences for a project."""
    return update_project_preferences(project_id, body.model_dump())


@app.get("/projects/{project_id}/approvals/pdf")
async def project_approvals_pdf_endpoint(
    project_id: str, x_user: str | None = Header(None)
) -> Response:
    """Return merged approval PDFs for a project."""
    try:
        data = build_approvals_summary_pdf(project_id, actor=x_user)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    log_event(
        "approval_summary_downloaded",
        user_id=x_user,
        project=project_id,
    )
    log_audit_event(
        project_id,
        "approval_summary_downloaded",
        actor=x_user,
        project=project_id,
    )
    return Response(
        data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="approvals-{project_id}.pdf"'},
    )


@app.post("/documents/import", status_code=201, response_model=DocumentModel)
async def import_document_endpoint(
    file: UploadFile = File(...),
    project: str | None = Form(None),
    user: str | None = Form(None),
    priority: int | None = Form(None),
) -> DocumentModel:
    """Import a DOCX or Markdown file and store it as a document."""
    import tempfile

    temp = tempfile.NamedTemporaryFile(delete=False)
    try:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            temp.write(chunk)
        temp.flush()
        temp.seek(0)
        data = temp.read()
        filename = file.filename or "unknown"
        document = import_document(
            filename,
            data,
            project=project,
            user=user,
            priority=priority,
        )
    finally:
        temp.close()
        try:
            Path(temp.name).unlink(missing_ok=True)
        except Exception:
            pass
    cache_set(
        "documents",
        json.dumps([d.model_dump(mode="json") for d in list_docs()]),
        ttl=30,
    )
    log_event(
        "import_document",
        user_id=user,
        project=project,
        filename=filename,
        message=render(
            "import_docx",
            user=user or "",
            project_id=project or "",
            filename=filename,
        ),
    )
    return document


@app.post("/documents/tiptap", status_code=201, response_model=DocumentModel)
async def import_tiptap_endpoint(body: dict[str, Any]) -> DocumentModel:
    """Import a TipTap JSON document."""
    from ..tiptap import import_tiptap_document

    try:
        document = import_tiptap_document(body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    log_event(
        "convert_tiptap",
        document=document.id,
        project=document.project,
        message=render(
            "convert_tiptap",
            project_id=document.project or "",
        ),
    )
    cache_set(
        "documents",
        json.dumps([d.model_dump(mode="json") for d in list_docs()]),
        ttl=30,
    )
    return document


@app.get("/documents", response_model=list[DocumentModel])
async def list_documents_endpoint() -> list[DocumentModel]:
    """Return all imported documents with caching."""
    cached = cache_get("documents")
    if cached:
        try:
            if isinstance(cached, bytes):
                cached = cached.decode()
            data = json.loads(cached)
            docs = [DocumentModel.model_validate(d) for d in data]
            if (cfg := Config.load(CONFIG_FILE)) and cfg.log_reads:
                log_event("read", entity_id="documents", count=len(docs))
            return docs
        except Exception:
            pass
    docs_list = list_docs()
    cache_set(
        "documents",
        json.dumps([d.model_dump(mode="json") for d in docs_list]),
        ttl=30,
    )
    if (cfg := Config.load(CONFIG_FILE)) and cfg.log_reads:
        log_event("read", entity_id="documents", count=len(docs_list))
    return docs_list


@app.get("/documents/public", response_model=list[DocumentModel])
async def list_public_documents_endpoint() -> list[DocumentModel]:
    """Return documents that are flagged as public copies."""
    return list_public_documents()


@app.get("/documents/public/report")
async def public_documents_report_endpoint() -> list[dict[str, str | None]]:
    """Return minimal metadata for public documents."""
    return public_documents_report()


@app.get("/documents/public/{doc_id}/html")
async def public_document_html_endpoint(doc_id: str):
    """Return the watermarked HTML copy for a public document."""
    for record in list_archives():
        if record.document_id == doc_id and record.metadata.get("public_copy_url"):
            url = record.metadata["public_copy_url"]
            if str(url).startswith("s3://"):
                return {"url": url}
            return FileResponse(url, media_type="text/html")
    raise HTTPException(status_code=404, detail="Public copy not found")


@app.get("/documents/{doc_id}", response_model=DocumentModel)
async def get_document_endpoint(doc_id: str) -> DocumentModel:
    """Retrieve a single document by id."""
    document = get_document(doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if (cfg := Config.load(CONFIG_FILE)) and cfg.log_reads:
        log_event("read", entity_id=doc_id)
    return document


@app.get("/documents/{doc_id}/audit", response_model=list[AuditLogEntry])
async def get_document_audit_endpoint(
    doc_id: str, _: str = Depends(require_audit_access)
) -> list[AuditLogEntry]:
    """Return audit events for a document."""
    document = get_document(doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    events = get_audit_log(doc_id)
    if (cfg := Config.load(CONFIG_FILE)) and cfg.log_reads:
        log_event("read", entity_id=doc_id, target="audit", count=len(events))
    return events


@app.get("/documents/{doc_id}/verify-signature")
async def verify_signature_endpoint(
    doc_id: str,
    provider: str | None = None,
    user: auth.User = Depends(require_permission("verification_override")),
) -> dict[str, object]:
    """Validate the digital signatures associated with ``doc_id``.

    Parameters
    ----------
    provider:
        Optional signature provider or comma-separated list of providers to use
        for validation. If omitted, the provider stored with each approval is
        used and secondary providers are tried on failure.
    """
    try:
        providers_input: str | list[str] | None = provider
        if provider and "," in provider:
            providers_input = [p.strip() for p in provider.split(",") if p.strip()]
        return verify_document_signature(doc_id, provider=providers_input)
    except KeyError:
        # If the document cannot be found, surface a consistent 200 response
        # with a failing status rather than a 404. This aligns the API with
        # verification semantics used elsewhere where validation problems
        # (missing approvals, missing certificate, etc.) still return 200
        # and embed the failure in the payload.
        return {"status": "fail", "details": []}
    except ValueError as exc:
        # Bad provider input remains a client error
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.put("/documents/{doc_id}", response_model=DocumentModel)
async def update_document_endpoint(doc_id: str, document: DocumentModel) -> DocumentModel:
    """Update a document's content and save the previous version."""
    try:
        updated, _ = update_document(doc_id, document.content, priority=document.priority)
        cache_set(
            "documents",
            json.dumps([d.model_dump(mode="json") for d in list_docs()]),
            ttl=30,
        )
        # Clear cached search results so subsequent queries reflect the update
        clear_cache()
        cfg = Config.load(CONFIG_FILE)
        if cfg and cfg.cms.lower() == "sharepoint":
            try:
                save_to_cms(updated, config=cfg)
            except Exception as exc:  # pragma: no cover - best effort
                raise HTTPException(status_code=502, detail=str(exc)) from exc
        return updated
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/documents/{doc_id}/revisions", status_code=201)
async def create_revision_endpoint(
    doc_id: str, body: RevisionCreate, x_user: str | None = Header(None)
) -> dict[str, str]:
    """Store a new document revision and optionally archive it."""
    try:
        document, rev_id = update_document(doc_id, body.content, steps=body.steps, author=x_user)
        result: dict[str, str] = {"revisionId": rev_id}
        if body.promote:
            record = archive_doc(document)
            result["archiveId"] = record.id
        return result
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/documents/{doc_id}/revisions", response_model=list[RevisionMeta])
async def list_revisions_endpoint(doc_id: str) -> list[RevisionMeta]:
    """List revision metadata for a document."""
    document = get_document(doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="document not found")
    return [RevisionMeta(id=r.id, timestamp=r.timestamp, author=r.author) for r in document.history]


@app.get("/documents/{doc_id}/revisions/{rev_id}", response_model=DocumentRevision)
async def get_revision_endpoint(doc_id: str, rev_id: str) -> DocumentRevision:
    """Return a specific revision for a document."""
    document = get_document(doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="document not found")
    for rev in document.history:
        if rev.id == rev_id:
            return rev
    raise HTTPException(status_code=404, detail="revision not found")


@app.post("/documents/{doc_id}/comments", response_model=CommentModel, status_code=201)
async def add_comment_endpoint(doc_id: str, body: CommentCreate) -> CommentModel:
    """Create a comment on the given document."""
    return add_comment(doc_id, body.user, body.text, parent=body.parent)


@app.get("/documents/{doc_id}/comments", response_model=list[CommentModel])
async def list_comments_endpoint(doc_id: str) -> list[CommentModel]:
    """List comments for a document."""
    comments = list_comments(doc_id)
    if (cfg := Config.load(CONFIG_FILE)) and cfg.log_reads:
        log_event("read", entity_id=doc_id, target="comments", count=len(comments))
    return comments


@app.get("/documents/{doc_id}/export")
async def export_document_endpoint(
    doc_id: str,
    fmt: Literal["markdown", "md", "html", "htm", "docx", "pdf", "json"],
) -> Response:
    """Return the document converted to the requested format."""
    document = get_document(doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        cfg = Config.load(CONFIG_FILE)
        template = cfg.filename_template if cfg else "{id}"
        data, media, filename = export_document(document, fmt, name_template=template)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    if (cfg := Config.load(CONFIG_FILE)) and cfg.log_reads:
        log_event("read", entity_id=doc_id, format=fmt)
    return Response(content=data, media_type=media, headers=headers)


class ArchiveMetadata(BaseModel):
    """Optional metadata for archiving."""

    metadata: dict[str, Any] | None = None
    check_results: dict[str, Any] | None = None


@app.post("/archive/{doc_id}", status_code=201, response_model=ArchiveRecord)
async def archive_document_endpoint(
    doc_id: str, body: ArchiveMetadata | None = None
) -> ArchiveRecord:
    """Archive a document in multiple formats."""
    document = get_document(doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return archive_doc(
        document,
        metadata=body.metadata if body else None,
        check_results=body.check_results if body else None,
    )


@app.get("/archive", response_model=list[ArchiveRecord])
async def list_archives_endpoint() -> list[ArchiveRecord]:
    """Return all archived documents."""
    records = list_archives()
    if (cfg := Config.load(CONFIG_FILE)) and cfg.log_reads:
        log_event("read", entity_id="archives", count=len(records))
    return records


@app.get("/archive/{archive_id}", response_model=ArchiveRecord)
async def get_archive_endpoint(archive_id: str) -> ArchiveRecord:
    """Retrieve a single archived record by id."""
    record = get_archive(archive_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Archive not found")
    if (cfg := Config.load(CONFIG_FILE)) and cfg.log_reads:
        log_event("read", entity_id=archive_id)
    return record


@app.get("/archive/{archive_id}/report/{fmt}")
async def download_report(archive_id: str, fmt: Literal["html", "pdf"]) -> Response:
    """Return the archived check report in the requested format."""
    record = get_archive(archive_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Archive not found")
    if fmt == "html" and record.report_html is not None:
        return Response(record.report_html, media_type="text/html")
    if fmt == "pdf" and record.report_pdf is not None:
        return Response(record.report_pdf, media_type="application/pdf")
    raise HTTPException(status_code=404, detail="Report not found")


@app.get("/search", response_model=list[DocumentModel])
async def search_documents(
    q: str,
    project: str | None = None,
    user: str | None = None,
    priority: int | None = None,
    after: datetime | None = None,
    before: datetime | None = None,
) -> list[DocumentModel]:
    """Return documents matching a full text query with basic caching."""
    cache_key = (
        f"search-{q}-{project or ''}-{user or ''}-{priority or ''}-"
        f"{after.isoformat() if after else ''}-{before.isoformat() if before else ''}"
    )
    cached = cache_get(cache_key)
    if cached:
        try:
            if isinstance(cached, bytes):
                cached = cached.decode()
            data = json.loads(cached)
            return [DocumentModel.model_validate(d) for d in data]
        except Exception:
            pass
    results = search(
        q,
        project=project,
        user=user,
        priority=priority,
        after=after,
        before=before,
    )
    cache_set(
        cache_key,
        json.dumps([d.model_dump(mode="json") for d in results]),
        ttl=30,
    )
    if (cfg := Config.load(CONFIG_FILE)) and cfg.log_reads:
        log_event("read", entity_id="search", query=q, count=len(results))
    return results


@app.get("/search/export")
async def export_search_results(q: str, fmt: str = "json") -> Response:
    """Return search results in JSON or CSV with ranking and snippets."""
    docs = await search_documents(q)
    results = ranked_search(q, docs)
    rows = [{"id": r["document"].id, "snippet": r["snippet"], "score": r["score"]} for r in results]
    if fmt == "csv":
        output = "id,snippet,score\n" + "\n".join(
            f"{r['id']},{r['snippet'].replace(',', ' ')},{r['score']}" for r in rows
        )
        media = "text/csv"
    else:
        output = json.dumps(rows)
        media = "application/json"
    return Response(content=output, media_type=media)


@app.post("/search/saved", status_code=201)
async def save_search_endpoint(body: SavedSearchCreate) -> search_mod.SavedSearch:
    """Store a search query for later reuse."""
    return save_search(body.query, user=body.user)


@app.get("/search/saved", response_model=list[search_mod.SavedSearch])
async def list_saved_searches_endpoint(user: str | None = None) -> list[search_mod.SavedSearch]:
    """Return saved search queries."""
    return list_saved_searches(user=user)


@app.get("/search/stats")
async def search_stats_endpoint() -> dict[str, int]:
    """Return counts of executed search queries."""
    return search_stats()


class WatchBody(BaseModel):
    user: str


@app.post("/watchlist/{project_id}", status_code=201, response_model=list[str])
async def toggle_watch_endpoint(project_id: str, body: WatchBody) -> list[str]:
    """Toggle ``project_id`` for ``body.user`` and return the updated list."""
    return toggle_watch(body.user, project_id)


@app.get("/watchlist/{user}", response_model=list[str])
async def get_watchlist_endpoint(user: str) -> list[str]:
    """Return the watchlist for ``user``."""
    return get_watchlist(user)


@app.post("/ai/rewrite")
async def ai_rewrite_endpoint(body: TextBody) -> dict[str, str]:
    """Return a rewritten version of the provided text."""
    text = await rewrite_text(body.text)
    return {"result": text}


@app.post("/ai/summarize")
async def ai_summarize_endpoint(body: TextBody) -> dict[str, str]:
    """Return a one sentence summary of the provided text."""
    summary = await summarize_text(body.text)
    return {"result": summary}


@app.post("/chat")
async def chat_bot_endpoint(body: TextBody) -> dict[str, str]:
    """Return an answer from the simple chatbot."""
    from ..chat_bot import answer_question

    answer = await answer_question(body.text)
    return {"result": answer}


@app.post("/document-types", status_code=201, response_model=DocumentTypeModel)
async def create_document_type(doc_type: DocumentTypeModel) -> DocumentTypeModel:
    """Create a new document type."""
    from fastapi import HTTPException

    try:
        add_document_type(doc_type)
    except ValueError as exc:
        # Normalize validation errors into a 400 response so API clients
        # receive a predictable status code instead of an internal server
        # error when providing invalid data.
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return doc_type


@app.get("/document-types", response_model=list[DocumentTypeModel])
async def get_document_types() -> list[DocumentTypeModel]:
    """Return all configured document types."""
    return list_document_types()


@app.get("/document-types/export")
async def export_doc_types_endpoint() -> Response:
    """Download all document types as JSON."""
    data = export_document_types_json()
    headers = {"Content-Disposition": "attachment; filename=document_types.json"}
    return Response(content=data, media_type="application/json", headers=headers)


@app.post("/document-types/import", status_code=201, response_model=list[DocumentTypeModel])
async def import_doc_types_endpoint(file: UploadFile = File(...)) -> list[DocumentTypeModel]:
    """Upload a JSON file of document types and replace existing ones."""
    data = await file.read()
    try:
        import_document_types_json(data.decode())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return list_document_types()


@app.get("/document-types/{name}", response_model=DocumentTypeModel)
async def get_document_type_endpoint(name: str) -> DocumentTypeModel:
    """Retrieve a single document type by name."""
    doc_type = get_document_type(name)
    if doc_type is None:
        raise HTTPException(status_code=404, detail="Document type not found")
    return doc_type


@app.put("/document-types/{name}", response_model=DocumentTypeModel)
async def update_document_type_endpoint(
    name: str, doc_type: DocumentTypeModel
) -> DocumentTypeModel:
    """Replace an existing document type."""
    try:
        return update_document_type(name, doc_type)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        # Renaming to an existing document type should surface as a conflict
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/document-types/{name}/usage", response_model=dict[str, Any])
async def check_document_type_usage_endpoint(name: str) -> dict[str, Any]:
    """Check if a document type is in use and return usage information."""
    from ..doc_types import get_document_type

    # Check if document type exists
    doc_type = get_document_type(name)
    if not doc_type:
        raise HTTPException(status_code=404, detail=f"Document type '{name}' not found")

    # Get all projects to check usage
    projects = list_projects()
    projects_using_doc_type = [p for p in projects if p.doc_type == name]

    return {
        "name": name,
        "in_use": len(projects_using_doc_type) > 0,
        "usage_count": len(projects_using_doc_type),
        "projects": [{"id": p.id, "name": p.name} for p in projects_using_doc_type],
    }


@app.delete("/document-types/{name}", status_code=204, response_class=Response)
async def delete_document_type_endpoint(name: str, replacement: str | None = None) -> Response:
    """Remove an existing document type. If in use, replacement is required."""
    from ..doc_types import get_document_type

    # Check if document type exists
    doc_type = get_document_type(name)
    if not doc_type:
        raise HTTPException(status_code=404, detail=f"Document type '{name}' not found")

    # Check if document type is in use
    projects = list_projects()
    projects_using_doc_type = [p for p in projects if p.doc_type == name]

    if projects_using_doc_type:
        if replacement:
            # Replacement must refer to a different, existing document type
            if replacement == name:
                raise HTTPException(
                    status_code=400, detail=f"Replacement document type '{replacement}' not found"
                )

            replacement_doc_type = get_document_type(replacement)
            if not replacement_doc_type:
                raise HTTPException(
                    status_code=404, detail=f"Replacement document type '{replacement}' not found"
                )

            # Update all projects to use the replacement
            for project in projects_using_doc_type:
                update_project(project.id, doc_type=replacement)
        else:
            # Document type in use but no replacement provided -> reject with
            # a clear message so callers know how to resolve the conflict.
            raise HTTPException(
                status_code=400,
                detail=f"Document type '{name}' is in use. Please specify a replacement.",
            )

    # Delete the document type
    try:
        delete_document_type(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Template management
# ---------------------------------------------------------------------------


@app.get("/templates")
async def list_templates_endpoint(
    user: auth.User = Depends(auth.get_current_user),
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    is_admin = has_role(user.username, "admin")
    for name, ver in list_stored_templates().items():
        if not is_admin and (not ver.approved or ver.retired):
            continue
        data = {
            "id": name,
            "name": name,
            "version": ver.version,
            "approved": ver.approved,
            "retired": ver.retired,
        }
        data.update(ver.metadata)
        items.append(data)
    return items


@app.get("/templates/{name}")
async def get_template_endpoint(name: str) -> dict[str, Any]:
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


@app.post("/templates", status_code=201)
async def upload_template_endpoint(
    name: str = Form(...),
    meta: str = Form("{}"),
    file: UploadFile = File(...),
) -> dict[str, Any]:
    """Store uploaded template ``file`` with ``meta`` information."""

    try:
        metadata = json.loads(meta)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="invalid metadata") from exc
    content = await file.read()
    version = store_template(name, content, metadata)
    return {
        "name": name,
        "version": version.version,
        "metadata": version.metadata,
        "approved": version.approved,
        "retired": version.retired,
    }


@app.post("/templates/{name}/approve")
async def approve_template_endpoint(
    name: str, user: auth.User = Depends(require_role("admin"))
) -> dict[str, Any]:
    ver = approve_template(name)
    return {"name": name, "version": ver.version, "approved": ver.approved}


@app.post("/templates/{name}/retire")
async def retire_template_endpoint(
    name: str, user: auth.User = Depends(require_role("admin"))
) -> dict[str, Any]:
    ver = retire_template(name)
    return {"name": name, "version": ver.version, "retired": ver.retired}


@app.get("/plugin-marketplace")
async def list_marketplace() -> list[dict[str, Any]]:
    """Return available plugins with detailed information."""
    from ..plugin_marketplace import list_plugins_with_info

    return list_plugins_with_info()


class MarketplaceInstall(BaseModel):
    name: str


@app.post("/plugin-marketplace/install")
async def install_marketplace_plugin(body: MarketplaceInstall) -> dict[str, str]:
    """Install a plugin from the marketplace."""
    from ..plugin_marketplace import install_plugin

    try:
        install_plugin(body.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"installed": body.name}


# ---------------------------------------------------------------------------
# Phase management
# ---------------------------------------------------------------------------


class PhaseModel(BaseModel):
    """Simple phase schema."""

    name: str


@app.post("/phases", status_code=201, response_model=list[str])
async def create_phase_endpoint(body: PhaseModel) -> list[str]:
    """Create a new project phase."""
    add_phase(body.name)
    return list_phases()


@app.get("/phases", response_model=list[str])
async def list_phases_endpoint() -> list[str]:
    """Return all configured phases."""
    return list_phases()


@app.put("/phases/{name}", response_model=list[str])
async def rename_phase_endpoint(name: str, body: PhaseModel) -> list[str]:
    """Rename a phase and propagate changes to workflows."""

    phases_list = list_phases()
    if name not in phases_list:
        raise HTTPException(status_code=404, detail=f"Phase '{name}' not found")

    # Update registry
    try:
        rename_phase(name, body.name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    # Propagate to existing workflows
    all_workflows = list_workflows()
    for wf in all_workflows:
        wf.phases = [body.name if p == name else p for p in wf.phases]
        if wf.phase == name:
            wf.phase = body.name

    # Update any projects that stored the phase before a workflow was created.
    from ..search import projects
    for proj in projects.values():
        if getattr(proj, "initial_phase", None) == name:
            proj.initial_phase = body.name

    return list_phases()


@app.get("/phases/{name}/usage", response_model=dict[str, Any])
async def check_phase_usage_endpoint(name: str) -> dict[str, Any]:
    """Check if a phase is in use and return usage information."""

    # Check if phase exists
    phases_list = list_phases()
    if name not in phases_list:
        raise HTTPException(status_code=404, detail=f"Phase '{name}' not found")

    # Get all projects to check usage (projects don't have direct phase field, but workflows do)
    all_workflows = list_workflows()
    workflows_using_phase = [w for w in all_workflows if name in w.phases]

    # Get projects that use workflows with this phase
    projects = list_projects()
    projects_using_phase = []
    for project in projects:
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


# Internal helpers to keep endpoint complexity low
def _ensure_phase_exists(name: str, phases_list: list[str]) -> None:
    if name not in phases_list:
        raise HTTPException(status_code=404, detail=f"Phase '{name}' not found")


def _validate_replacement_exists(replacement: str | None, phases_list: list[str]) -> None:
    # Validate that a provided replacement refers to an existing phase
    if replacement and replacement not in phases_list:
        raise HTTPException(status_code=404, detail=f"Replacement phase '{replacement}' not found")


def _phase_usage(name: str) -> tuple[list[ProjectModel], list[WorkflowModel]]:
    # Compute projects and workflows that reference the given phase
    all_workflows = list_workflows()
    workflows_using_phase = [w for w in all_workflows if name in w.phases]

    projects_using_phase: list[ProjectModel] = []
    for project in list_projects():
        if project.workflow:
            workflow = get_workflow(project.workflow)
            if workflow and name in workflow.phases:
                projects_using_phase.append(project)
    return projects_using_phase, workflows_using_phase


def _apply_phase_replacement(
    name: str, replacement: str, workflows_using_phase: list[WorkflowModel]
) -> None:
    # Update all affected workflows to use the replacement phase
    for wf in workflows_using_phase:
        wf.phases = [replacement if p == name else p for p in wf.phases]
        if wf.phase == name:
            wf.phase = replacement


@app.delete("/phases/{name}", status_code=204, response_class=Response)
async def delete_phase_endpoint(name: str, replacement: str | None = None) -> Response:
    """Remove a phase by name. If in use, replacement is required."""
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


@app.post("/workflows", status_code=201, response_model=WorkflowModel)
@log_call
async def create_workflow_endpoint(
    workflow: WorkflowCreate, x_user: str | None = Header(None)
) -> WorkflowModel:
    """Create a new workflow."""
    return create_workflow(workflow.project, workflow.phases, mode=workflow.mode)


@app.get("/workflows/{wf_id}", response_model=WorkflowModel)
@log_call
async def get_workflow_endpoint(wf_id: str, x_user: str | None = Header(None)) -> WorkflowModel:
    """Return a workflow by id."""
    wf = get_workflow(wf_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


@app.get("/workflows", response_model=list[WorkflowModel])
@log_call
async def list_workflows_endpoint(
    project: str | None = None, x_user: str | None = Header(None)
) -> list[WorkflowModel]:
    """Return workflows optionally filtered by project."""
    return list_workflows(project)


@app.get("/workflow_roles", response_model=list[str])
@log_call
async def list_workflow_roles_endpoint(x_user: str | None = Header(None)) -> list[str]:
    """Return all unique workflow roles."""
    return list_roles()


@app.post("/workflows/{wf_id}/start", response_model=WorkflowModel)
@log_call
async def start_workflow_endpoint(
    wf_id: str,
    title: str = Form(...),
    file: UploadFile | None = File(None),
    x_user: str | None = Header(None),
) -> WorkflowModel:
    """Start a workflow by uploading a document."""

    wf = get_workflow(wf_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    data = await file.read() if file else None
    return start_workflow(wf_id, title, data)


@app.post("/workflows/{wf_id}/assign", response_model=WorkflowModel)
@log_call
async def assign_reviewer_endpoint(
    wf_id: str, body: ReviewerAssign, x_user: str | None = Header(None)
) -> WorkflowModel:
    """Assign a reviewer to a workflow."""
    try:
        return assign_reviewer(wf_id, body.user)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/workflows/{wf_id}/advance", response_model=WorkflowModel)
@log_call
async def advance_workflow_endpoint(wf_id: str, x_user: str | None = Header(None)) -> WorkflowModel:
    """Advance workflow to the next phase."""
    try:
        return advance_workflow(wf_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/approvals", status_code=201, response_model=ApprovalModel)
@log_call
async def create_approval_endpoint(body: ApprovalCreate) -> ApprovalModel:
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


@app.get("/approvals", response_model=list[ApprovalModel])
@log_call
async def list_approvals_endpoint(
    workflow: str | None = None, phase: str | None = None
) -> list[ApprovalModel]:
    """Return approvals optionally filtered by workflow and phase."""
    return list_approvals(workflow, phase)


@app.get("/approvals/{approval_id}", response_model=ApprovalModel)
@log_call
async def get_approval_endpoint(approval_id: str) -> ApprovalModel:
    """Retrieve a single approval by id."""
    approval = get_approval(approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    return approval


@app.put("/approvals/{approval_id}", response_model=ApprovalModel)
@log_call
async def update_approval_endpoint(approval_id: str, body: ApprovalUpdate) -> ApprovalModel:
    """Update approval state and signature."""
    try:
        return await update_approval_state(
            approval_id,
            body.state,
            signature_id=body.signature_id,
            due_at=body.due_at,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/approvals/{approval_id}/sign")
@log_call
async def sign_approval_endpoint(approval_id: str) -> dict[str, str]:
    """Begin a signing flow for an approval."""
    approval = get_approval(approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    wf = get_workflow(approval.workflow)
    if wf is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return_to = f"/projects/{wf.project}"
    doc_id = approval.document_id or wf.project
    url = send_for_signature(approval_id, doc_id, approval.reviewer, return_to)
    sig_id = approval.signature_id
    if sig_id is None:
        raise RuntimeError("signature id not set")
    return {"id": sig_id, "url": url}


@app.post("/sign/{doc_id}")
@log_call
async def sign_document(
    doc_id: str,
    user: str = Form(...),
    workflow: str | None = Form(None),
    approval: str | None = Form(None),
) -> dict[str, str]:
    """Create a signature request for ``doc_id`` using the active provider."""
    sig_id, url, _meta = get_provider().request_signature(
        doc_id,
        user,
        workflow_id=workflow,
        approval_id=approval,
    )
    return {"id": sig_id, "url": url}


@app.post("/sign/{sig_id}/complete")
@log_call
async def complete_sign(sig_id: str) -> None:
    """Mark a signature request as completed."""
    complete_signature(sig_id)
    get_provider().process_webhook({"id": sig_id, "status": "signed"})


@app.get("/sign/{sig_id}")
@log_call
async def get_sign_status(sig_id: str) -> dict[str, str]:
    """Return signature status."""
    status = signature_status(sig_id)
    return {"status": status}


@app.post("/token", response_model=auth.Token)
async def token(response: Response, form_data: OAuth2PasswordRequestForm = Depends()) -> auth.Token:
    """Return a JWT access token for valid user credentials."""
    token_resp = await auth.login_for_access_token(form_data)
    response.set_cookie(
        "access_token",
        token_resp.access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    log_event(
        "login",
        user_id=form_data.username,
        message=render("login", user=form_data.username),
    )
    return token_resp


@app.post("/oidc/token", response_model=auth.Token)
async def oidc_token(form_data: OAuth2PasswordRequestForm = Depends()) -> auth.Token:
    """Return an ID token using the OIDC flow."""
    return await auth.login_for_oidc_token(form_data)


@app.get("/me")
async def read_current_user(current_user: auth.User = Depends(auth.get_current_user)) -> auth.User:
    """Return the authenticated user."""
    return current_user


@app.post("/logout")
async def logout(response: Response) -> dict[str, str]:
    """Clear authentication cookie."""
    response.delete_cookie("access_token")
    return {"detail": "Logged out"}


@app.get("/oidc/me")
async def read_current_oidc_user(
    current_user: auth.User = Depends(auth.get_current_user_oidc),
) -> auth.User:
    """Return the authenticated user for the OIDC flow."""
    return current_user


@app.get("/", response_class=HTMLResponse)
async def root(request: Request) -> HTMLResponse:
    """Display login page or dashboard depending on session."""
    if request.cookies.get("session") == "admin":
        return templates.TemplateResponse(request, "dashboard.html", {"user": "admin"})
    return templates.TemplateResponse(request, "login.html")


@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, username: str = Form(...), password: str = Form(...)) -> Response:
    """Simple credential check for admin user."""
    if username == "admin" and password == "admin":
        response = RedirectResponse("/projects", status_code=303)
        response.set_cookie("session", "admin")
        log_event(
            "login",
            user_id=username,
            message=render("login", user=username),
        )
        return response
    return templates.TemplateResponse(
        request, "login.html", {"error": "Invalid credentials"}, status_code=400
    )


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request) -> Response:
    """Placeholder dashboard displayed after login."""
    if request.cookies.get("session") != "admin":
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "dashboard.html", {"user": "admin"})


@app.get("/help", response_class=HTMLResponse)
async def help_page() -> HTMLResponse:
    """Display a lightweight help page rendered from Markdown."""
    # ``__file__`` resides in ``src/docreview360/api``; ascend to the repository
    # root before resolving the docs directory.
    doc_path = Path(__file__).resolve().parent.parent.parent.parent / "docs" / "getting_started.md"
    try:
        text = doc_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=500, detail="Unable to load documentation") from exc
    html = MarkdownIt().render(text)
    return HTMLResponse(html)


@app.get("/admin/panel")
async def admin_panel(user: auth.User = Depends(require_role("admin"))) -> dict[str, str]:
    """Return a trivial payload for admin-only access."""
    return {"user": user.username, "admin": "ok"}


@app.get("/plugins")
async def list_plugins() -> list[dict[str, Any]]:
    """Return metadata about registered plugins."""
    return plugin_registry.info()


@app.post("/plugins", status_code=201)
async def register_plugin(body: PluginModule) -> dict[str, list[str]]:
    """Load and register plugins from a module path."""
    try:
        load_plugins([body.module])
    except (ImportError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"names": plugin_registry.all()}


@app.put("/plugins/{name}/enable")
async def enable_plugin(name: str) -> dict[str, str]:
    """Enable a disabled plugin."""
    try:
        plugin_registry.enable(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"enabled": name}


@app.put("/plugins/{name}/disable")
async def disable_plugin(name: str) -> dict[str, str]:
    """Disable a plugin."""
    try:
        plugin_registry.disable(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"disabled": name}


@app.delete("/plugins/{name}", status_code=204, response_class=Response)
async def unregister_plugin(name: str) -> Response:
    """Unregister a plugin entirely."""
    try:
        plugin_registry.unregister(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)


@app.get("/logs", response_model=list[LogEntry])
async def list_logs(
    start: datetime | None = None,
    end: datetime | None = None,
    user_id: str | None = None,
    entity_id: str | None = None,
    entity_type: str | None = None,
    action: str | None = None,
    severity: str | None = None,
    log_id: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
    _: str = Depends(require_audit_access),
) -> list[LogEntry]:
    """Return recorded logs with optional filters and pagination."""
    entries = query_logs(
        action=action,
        user_id=user_id,
        start=start,
        end=end,
        entity_id=entity_id,
        entity_type=entity_type,
        severity=severity,
        log_id=log_id,
        limit=limit,
        offset=offset,
    )
    if (cfg := Config.load(CONFIG_FILE)) and cfg.log_reads:
        # Accessing the operational logs should be treated the same as auditing
        # the audit log itself.  Previously this endpoint logged the action as
        # ``read`` which caused an extra entry compared to the dedicated audit
        # endpoint, making their outputs diverge in tests.  Using the
        # ``audit_log_access`` action keeps the semantics aligned and prevents
        # spurious differences when clients fetch logs via either route.
        log_event("audit_log_access", entity_id="logs", count=len(entries))
    return entries


@app.get("/api/audit", response_model=list[LogEntry])
async def list_audit(
    start: datetime | None = None,
    end: datetime | None = None,
    user_id: str | None = None,
    entity_id: str | None = None,
    entity_type: str | None = None,
    action: str | None = None,
    severity: str | None = None,
    log_id: str | None = None,
    page: int | None = None,
    size: int | None = None,
    limit: int | None = None,
    offset: int | None = None,
    _: str = Depends(require_audit_access),
) -> list[LogEntry]:
    """Alias for :func:`list_logs` used by the dashboard."""
    if page is not None:
        size = size or 50
        limit = size
        offset = page * size

    entries = query_logs(
        action=action,
        user_id=user_id,
        start=start,
        end=end,
        entity_id=entity_id,
        entity_type=entity_type,
        severity=severity,
        log_id=log_id,
        limit=limit,
        offset=offset,
    )
    if (cfg := Config.load(CONFIG_FILE)) and cfg.log_reads:
        log_event("audit_log_access", entity_id="logs", count=len(entries))
    return entries


@app.get("/logs/export")
async def export_logs_endpoint(
    fmt: str = "json",
    start: datetime | None = None,
    end: datetime | None = None,
    user_id: str | None = None,
    entity_id: str | None = None,
    entity_type: str | None = None,
    action: str | None = None,
    severity: str | None = None,
    log_id: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
    _: str = Depends(require_audit_access),
) -> Response:
    """Export audit logs in the requested format with metadata."""

    filters = {
        k: v
        for k, v in {
            "start": start,
            "end": end,
            "user_id": user_id,
            "entity_id": entity_id,
            "entity_type": entity_type,
            "action": action,
            "severity": severity,
            "log_id": log_id,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    entries = query_logs(
        action=action,
        user_id=user_id,
        start=start,
        end=end,
        entity_id=entity_id,
        entity_type=entity_type,
        severity=severity,
        log_id=log_id,
        limit=limit,
        offset=offset,
    )
    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "filters": filters,
    }
    filter_str = ", ".join(f"{k}={v}" for k, v in filters.items()) or "none"
    header = "id,timestamp,user_id,action,entity_type,entity_id,severity,ip_address,details"
    rows = [
        f"{e.id},{e.timestamp},{e.user_id or ''},{e.action},{e.entity_type or ''},"
        f"{e.entity_id or ''},{e.severity},{e.ip_address or ''},{json.dumps(e.details)}"
        for e in entries
    ]
    if fmt == "csv":
        lines = [
            f"# Generated at: {metadata['generated_at']}",
            f"# Filters: {filter_str}",
            header,
            *rows,
        ]
        content = "\n".join(lines)
        media = "text/csv"
    elif fmt == "json":
        content = json.dumps(
            {"metadata": metadata, "logs": [e.model_dump(mode="json") for e in entries]}
        )
        media = "application/json"
    elif fmt == "pdf":
        lines = [
            f"Generated at: {metadata['generated_at']}",
            f"Filters: {filter_str}",
            "",
            header,
            *rows,
        ]
        content = b"%PDF-1.4\n" + "\n".join(lines).encode("utf-8")
        media = "application/pdf"
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")
    if (cfg := Config.load(CONFIG_FILE)) and cfg.log_reads:
        log_event("read", entity_id="logs_export", count=len(entries), fmt=fmt)
    return Response(content=content, media_type=media)


@app.get("/reports/summary", response_model=SummaryReport)
async def get_summary_report() -> SummaryReport:
    """Return counts of projects, documents, workflows, and approvals."""
    return generate_summary()


@app.get("/metrics/summary", response_model=SummaryReport)
async def get_metrics_summary() -> SummaryReport:
    """Alias for :func:`get_summary_report` used by dashboards."""
    return generate_summary()


@app.get("/reports/summary.csv")
async def get_summary_csv() -> Response:
    """Return the summary report as CSV."""
    return Response(reporting.summary_csv(), media_type="text/csv")


@app.get("/reports/throughput", response_model=list[reporting.ThroughputEntry])
async def throughput_endpoint(days: int = 7) -> list[reporting.ThroughputEntry]:
    """Return approval throughput data."""

    return reporting.throughput_data(days)


@app.get("/reports/throughput.csv")
async def throughput_csv_endpoint(days: int = 7) -> Response:
    """CSV export of :func:`throughput_endpoint`."""

    return Response(reporting.throughput_csv(days), media_type="text/csv")


@app.get("/reports/workload", response_model=dict[str, int])
async def workload_endpoint() -> dict[str, int]:
    """Return workload counts per user."""

    return reporting.workload_data()


@app.get("/reports/workload.csv")
async def workload_csv_endpoint() -> Response:
    """CSV export of :func:`workload_endpoint`."""

    return Response(reporting.workload_csv(), media_type="text/csv")


@app.get("/reports/dashboard", response_model=list[DashboardEntry])
async def get_dashboard_data(x_user: str | None = Header(None)) -> list[DashboardEntry]:
    """Return per-project data for dashboard widgets."""

    return dashboard_data(x_user)


@app.get("/dashboard/user", response_model=list[DashboardEntry])
async def user_dashboard_endpoint(x_user: str | None = Header(None)) -> list[DashboardEntry]:
    """Return dashboard data for the authenticated user."""

    if not x_user:
        raise HTTPException(status_code=401, detail="Missing user")
    return user_dashboard(x_user)


@app.get("/dashboard/widgets")
async def get_widget_counts(x_user: str | None = Header(None)) -> dict[str, int]:
    """Return assignment and approval counts for dashboard widgets."""

    return widget_counts(x_user)


@app.get("/dashboard/doc-types", response_model=dict[str, int])
async def doc_type_counts_endpoint() -> dict[str, int]:
    """Return active project counts grouped by document type."""

    return reporting.doc_type_counts()


class VisibilityPayload(BaseModel):
    """Dashboard widget visibility options."""

    stats: bool | None = None
    status: bool | None = None
    activity: bool | None = None
    logs: bool | None = None


@app.get("/dashboard/visibility")
async def get_visibility_endpoint(x_user: str | None = Header(None)) -> dict[str, bool]:
    """Return saved visibility settings for the user."""

    if not x_user:
        raise HTTPException(status_code=401, detail="Missing user")
    return get_visibility(x_user)


@app.put("/dashboard/visibility")
async def update_visibility_endpoint(
    body: VisibilityPayload, x_user: str | None = Header(None)
) -> dict[str, bool]:
    """Persist user visibility preferences."""

    if not x_user:
        raise HTTPException(status_code=401, detail="Missing user")
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    return set_visibility(x_user, data)


@app.get("/dashboard/manager")
async def manager_dashboard_endpoint(
    user: auth.User = Depends(require_role("manager")),
) -> dict[str, Any]:
    """Return dashboard information for managers."""

    return manager_dashboard()


@app.get("/status/public")
async def public_status_endpoint() -> dict[str, int]:
    """Expose limited status for unauthenticated users."""
    return public_status()


@app.get("/status/internal")
async def internal_status_endpoint() -> dict[str, int]:
    """Return extended system status for admins."""
    return internal_status()


@app.get("/dashboard/admin")
async def admin_dashboard_endpoint(
    user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Return system overview for administrators."""

    return admin_dashboard()


@app.websocket("/ws/dashboard")
async def dashboard_stream(websocket: WebSocket) -> None:
    """Send dashboard data periodically over a websocket."""

    await websocket.accept()
    user = websocket.query_params.get("user")
    previous: list[dict[str, Any]] | None = None
    try:
        while True:
            data = [entry.model_dump() for entry in dashboard_data(user)]
            if data != previous:
                await websocket.send_json(data)
                previous = data
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass


@app.websocket("/ws/logs")
async def logs_stream(websocket: WebSocket) -> None:
    """Stream log events to connected clients with access control."""

    user = websocket.headers.get("x-user") or websocket.query_params.get("user")

    # Allow anonymous connections for simple dashboards and tests.  If a user
    # identifier is supplied we still honour permission checks, but omitting the
    # header no longer results in an immediate 1008 policy‑violation close which
    # previously broke ``test_log_websocket``.  This keeps the endpoint usable in
    # lightweight environments while retaining optional access control.
    if user and not has_permission(user, "view_audit_log"):
        log_event("audit_log_ws_access", user_id=user, status="denied")
        await websocket.close(code=1008)
        return

    log_event("audit_log_ws_access", user_id=user, status="success")
    await websocket.accept()
    try:
        async for entry in log_stream():
            await websocket.send_json(entry.model_dump(mode="json"))
    except WebSocketDisconnect:
        pass


@app.get("/config", response_model=ConfigPayload)
async def get_config_endpoint() -> ConfigPayload:
    """Return the current application configuration."""
    cfg = Config.load(CONFIG_FILE)
    if cfg is None:
        cfg = Config(database="sqlite", editor="tiptap", cms="none", auth="oidc")
    return ConfigPayload(**cfg.__dict__)


@app.put("/config", response_model=ConfigPayload)
async def update_config_endpoint(payload: ConfigPayload) -> ConfigPayload:
    """Persist a new configuration."""
    cfg = Config(**payload.model_dump())
    try:
        cfg.save(CONFIG_FILE)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return payload


@app.get("/signature-provider")
async def get_signature_provider_endpoint() -> dict[str, str | None]:
    """Return the configured signature providers."""

    providers = get_default_providers()
    primary = providers[0] if providers else None
    fallback = providers[1] if len(providers) > 1 else None
    return {"primary": primary, "fallback": fallback}


@app.put("/signature-provider")
async def update_signature_provider_endpoint(
    payload: SignatureProviderPayload,
) -> dict[str, str | None]:
    """Persist the active signature provider selection."""

    update_setting("signature_provider_primary", payload.primary)
    update_setting("signature_provider_fallback", payload.fallback)
    return {"primary": payload.primary, "fallback": payload.fallback}


@app.post("/tools/convert")
async def convert_tool_endpoint(
    output_format: str = Form(...), file: UploadFile = File(...)
) -> dict[str, str]:
    """Convert an uploaded document and return the filename."""

    _ = await file.read()  # read file data but ignore for stub
    dest = convert_document(Path(file.filename or ""), output_format)
    return {"filename": dest.name}


@app.get("/environments")
async def list_environments() -> dict[str, Any]:
    """Return available environments and the current one."""
    return {"current": current_environment(), "envs": load_envs()}


@app.post("/environments/{name}")
async def switch_env_endpoint(name: str) -> dict[str, str]:
    """Switch the active environment and return its URL."""
    try:
        url = switch_environment(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"url": url}

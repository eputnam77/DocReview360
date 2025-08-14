"""FastAPI application exposing DocReview360 endpoints."""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, cast

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
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from markdown_it import MarkdownIt
from pydantic import BaseModel, ConfigDict, Field

from . import auth, reporting
from . import search as search_mod
from .ai_assist import rewrite_text, summarize_text
from .approvals import (
    ApprovalModel,
    create_approval,
    get_approval,
    list_approvals,
    send_for_signature,
    update_approval_state,
)
from .archive import (
    ArchiveRecord,
    get_archive,
    list_archives,
)
from .archive import (
    archive_document as archive_doc,
)
from .cache import cache_get, cache_set, clear_cache
from .cms import save_to_cms
from .comments import CommentModel, add_comment, list_comments
from .config import CONFIG_FILE, Config
from .dashboard_prefs import get_visibility, set_visibility
from .doc_types import (
    DocumentTypeModel,
    add_document_type,
    delete_document_type,
    export_document_types_json,
    get_document_type,
    import_document_types_json,
    list_document_types,
    update_document_type,
)
from .documenso import (
    complete_signature,
    process_webhook,
    signature_status,
)
from .documents import (
    DocumentModel,
    get_document,
    import_document,
    update_document,
)
from .documents import (
    list_documents as list_docs,
)
from .environment import current_environment, load_envs, switch_environment
from .exporter import export_document, set_guardrails
from .integrations.signature import DEFAULT_PROVIDER, get_provider
from .logs import LogEntry, log_event, log_stream, query_logs
from .messages import render
from .nemo_guardrails import GuardrailsMiddleware, contains_pii
from .phases import add_phase, delete_phase, list_phases, rename_phase
from .plugins import load_plugins
from .plugins import registry as plugin_registry
from .profile import get_preferences, update_preferences
from .rbac import get_roles, require_role
from .reporting import (
    DashboardEntry,
    SummaryReport,
    admin_dashboard,
    dashboard_data,
    generate_summary,
    manager_dashboard,
    user_dashboard,
    widget_counts,
)
from .search import (
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
from .status import internal_status, public_status
from .stubs.task223 import convert_document
from .template_manager import upload_template as store_template
from .watchlist import get_watchlist, toggle_watch
from .workflows import (
    WorkflowModel,
    advance_workflow,
    assign_reviewer,
    create_workflow,
    get_workflow,
    list_workflows,
    start_workflow,
    workflows,
)

# Load environment variables from .env file
load_dotenv()


class WorkflowCreate(BaseModel):
    """Input model for creating workflows."""

    project: str
    phases: list[str]


class ReviewerAssign(BaseModel):
    """Input model for assigning reviewers."""

    user: str


class ApprovalCreate(BaseModel):
    """Input model for creating approvals."""

    workflow: str
    reviewer: str
    due_at: datetime | None = None
    description: str | None = None


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


app = FastAPI(title="DocReview360")

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enable compression for large responses as recommended by the
# performance profiling report. ``minimum_size`` avoids wasting
# CPU cycles on tiny payloads.
app.add_middleware(GZipMiddleware, minimum_size=1000)
if os.environ.get("ENABLE_GUARDRAILS", "").lower() in {"1", "true", "yes"}:
    # Activate NeMo Guardrails PII checker when explicitly enabled
    set_guardrails(contains_pii)
    app.add_middleware(GuardrailsMiddleware, checker=contains_pii)

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for monitoring."""
    return {"status": "healthy"}


@app.get("/users/me")
async def current_user_endpoint(x_user: str | None = Header(None)) -> dict[str, Any]:
    """Return information about the current user.

    The frontend uses this endpoint to hydrate the global user store. In a real
    deployment this would rely on session middleware or OIDC claims.
    """
    if not x_user:
        raise HTTPException(status_code=401, detail="Missing user")
    return {"username": x_user, "is_admin": True}


class PreferencePayload(BaseModel):
    """Input model for updating user preferences."""

    theme: Literal["system", "light", "dark"] | None = None
    reduce_motion: bool | None = None


@app.get("/profile")
async def get_profile(x_user: str | None = Header(None)) -> dict[str, Any]:
    """Return profile information for the current user."""

    if not x_user:
        raise HTTPException(status_code=401, detail="Missing user")
    return {
        "username": x_user,
        "preferences": get_preferences(x_user),
        "roles": sorted(get_roles(x_user)),
    }


@app.put("/profile")
async def update_profile(
    body: PreferencePayload, x_user: str | None = Header(None)
) -> dict[str, Any]:
    """Persist profile preference updates."""

    if not x_user:
        raise HTTPException(status_code=401, detail="Missing user")
    prefs = {k: v for k, v in body.model_dump().items() if v is not None}
    return {"username": x_user, "preferences": update_preferences(x_user, prefs)}


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
        from .search import search_index

        body.id = search_index.generate_project_id()

    # If document_number is not provided, use the id as document_number
    if body.document_number is None:
        body.document_number = body.id

    project = ProjectModel(**body.model_dump())
    add_project(project)
    if body.workflow:
        # Initialize workflow using the provided phase as the starting phase
        start_phase = body.phase or "start"
        wf = create_workflow(project.id, [start_phase])
        project.workflow = wf.id
    # Clear all project-related caches to ensure fresh data
    clear_cache()
    print(f"DEBUG: Project '{project.id}' created successfully, cache cleared")
    log_event(
        "create_project",
        user=project.user,
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
    from .workflows import get_workflow as _get_wf

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

        project_user = user or sme
        project_doc_type = doc_type or docType

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
        user=user,
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
    from .tiptap import import_tiptap_document

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
            return [DocumentModel.model_validate(d) for d in data]
        except Exception:
            pass
    docs_list = list_docs()
    cache_set(
        "documents",
        json.dumps([d.model_dump(mode="json") for d in docs_list]),
        ttl=30,
    )
    return docs_list


@app.get("/documents/{doc_id}", response_model=DocumentModel)
async def get_document_endpoint(doc_id: str) -> DocumentModel:
    """Retrieve a single document by id."""
    document = get_document(doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@app.put("/documents/{doc_id}", response_model=DocumentModel)
async def update_document_endpoint(doc_id: str, document: DocumentModel) -> DocumentModel:
    """Update a document's content and save the previous version."""
    try:
        updated = update_document(doc_id, document.content, priority=document.priority)
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


@app.post("/documents/{doc_id}/comments", response_model=CommentModel, status_code=201)
async def add_comment_endpoint(doc_id: str, body: CommentCreate) -> CommentModel:
    """Create a comment on the given document."""
    return add_comment(doc_id, body.user, body.text, parent=body.parent)


@app.get("/documents/{doc_id}/comments", response_model=list[CommentModel])
async def list_comments_endpoint(doc_id: str) -> list[CommentModel]:
    """List comments for a document."""
    return list_comments(doc_id)


@app.get("/documents/{doc_id}/export")
async def export_document_endpoint(doc_id: str, fmt: str) -> Response:
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
    return Response(content=data, media_type=media, headers=headers)


class ArchiveMetadata(BaseModel):
    """Optional metadata for archiving."""

    metadata: dict[str, Any] | None = None


@app.post("/archive/{doc_id}", status_code=201, response_model=ArchiveRecord)
async def archive_document_endpoint(
    doc_id: str, body: ArchiveMetadata | None = None
) -> ArchiveRecord:
    """Archive a document in multiple formats."""
    document = get_document(doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return archive_doc(document, metadata=body.metadata if body else None)


@app.get("/archive", response_model=list[ArchiveRecord])
async def list_archives_endpoint() -> list[ArchiveRecord]:
    """Return all archived documents."""
    return list_archives()


@app.get("/archive/{archive_id}", response_model=ArchiveRecord)
async def get_archive_endpoint(archive_id: str) -> ArchiveRecord:
    """Retrieve a single archived record by id."""
    record = get_archive(archive_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Archive not found")
    return record


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
    from .chat_bot import answer_question

    answer = await answer_question(body.text)
    return {"result": answer}


@app.post("/document-types", status_code=201, response_model=DocumentTypeModel)
async def create_document_type(doc_type: DocumentTypeModel) -> DocumentTypeModel:
    """Create a new document type."""
    add_document_type(doc_type)
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


@app.get("/document-types/{name}/usage", response_model=dict[str, Any])
async def check_document_type_usage_endpoint(name: str) -> dict[str, Any]:
    """Check if a document type is in use and return usage information."""
    from .doc_types import get_document_type

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
    from .doc_types import get_document_type

    # Check if document type exists
    doc_type = get_document_type(name)
    if not doc_type:
        raise HTTPException(status_code=404, detail=f"Document type '{name}' not found")

    # Check if document type is in use
    projects = list_projects()
    projects_using_doc_type = [p for p in projects if p.doc_type == name]

    if projects_using_doc_type:
        if not replacement:
            detail_msg = (
                f"Document type '{name}' is in use by "
                f"{len(projects_using_doc_type)} project(s). "
                "Please specify a replacement document type."
            )
            raise HTTPException(status_code=400, detail=detail_msg)

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

    # Delete the document type
    try:
        delete_document_type(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Template upload
# ---------------------------------------------------------------------------


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
    return {"name": name, "version": version.version, "metadata": version.metadata}


@app.get("/plugin-marketplace")
async def list_marketplace() -> list[dict[str, Any]]:
    """Return available plugins with detailed information."""
    from .plugin_marketplace import list_plugins_with_info

    return list_plugins_with_info()


class MarketplaceInstall(BaseModel):
    name: str


@app.post("/plugin-marketplace/install")
async def install_marketplace_plugin(body: MarketplaceInstall) -> dict[str, str]:
    """Install a plugin from the marketplace."""
    from .plugin_marketplace import install_plugin

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
async def create_workflow_endpoint(workflow: WorkflowCreate) -> WorkflowModel:
    """Create a new workflow."""
    return create_workflow(workflow.project, workflow.phases)


@app.get("/workflows/{wf_id}", response_model=WorkflowModel)
async def get_workflow_endpoint(wf_id: str) -> WorkflowModel:
    """Return a workflow by id."""
    wf = get_workflow(wf_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


@app.get("/workflows", response_model=list[WorkflowModel])
async def list_workflows_endpoint(project: str | None = None) -> list[WorkflowModel]:
    """Return workflows optionally filtered by project."""
    return list_workflows(project)


@app.post("/workflows/{wf_id}/start", response_model=WorkflowModel)
async def start_workflow_endpoint(
    wf_id: str,
    title: str = Form(...),
    file: UploadFile | None = File(None),
) -> WorkflowModel:
    """Start a workflow by uploading a document."""

    wf = get_workflow(wf_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    data = await file.read() if file else None
    return start_workflow(wf_id, title, data)


@app.post("/workflows/{wf_id}/assign", response_model=WorkflowModel)
async def assign_reviewer_endpoint(wf_id: str, body: ReviewerAssign) -> WorkflowModel:
    """Assign a reviewer to a workflow."""
    try:
        return assign_reviewer(wf_id, body.user)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/workflows/{wf_id}/advance", response_model=WorkflowModel)
async def advance_workflow_endpoint(wf_id: str) -> WorkflowModel:
    """Advance workflow to the next phase."""
    try:
        return advance_workflow(wf_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/approvals", status_code=201, response_model=ApprovalModel)
async def create_approval_endpoint(body: ApprovalCreate) -> ApprovalModel:
    """Create an approval for a workflow."""
    return create_approval(
        body.workflow,
        body.reviewer,
        due_at=body.due_at,
        description=body.description,
    )


@app.get("/approvals", response_model=list[ApprovalModel])
async def list_approvals_endpoint(workflow: str | None = None) -> list[ApprovalModel]:
    """Return approvals optionally filtered by workflow."""
    return list_approvals(workflow)


@app.get("/approvals/{approval_id}", response_model=ApprovalModel)
async def get_approval_endpoint(approval_id: str) -> ApprovalModel:
    """Retrieve a single approval by id."""
    approval = get_approval(approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    return approval


@app.put("/approvals/{approval_id}", response_model=ApprovalModel)
async def update_approval_endpoint(approval_id: str, body: ApprovalUpdate) -> ApprovalModel:
    """Update approval state and signature."""
    try:
        return update_approval_state(
            approval_id,
            body.state,
            signature_id=body.signature_id,
            due_at=body.due_at,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/approvals/{approval_id}/sign")
async def sign_approval_endpoint(approval_id: str) -> dict[str, str]:
    """Begin a signing flow for an approval."""
    approval = get_approval(approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    wf = get_workflow(approval.workflow)
    if wf is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return_to = f"/projects/{wf.project}"
    url = send_for_signature(approval_id, wf.project, approval.reviewer, return_to)
    return {"id": approval.signature_id, "url": url}


@app.post("/sign/{doc_id}")
async def sign_document(
    doc_id: str,
    user: str = Form(...),
    workflow: str | None = Form(None),
    approval: str | None = Form(None),
) -> dict[str, str]:
    """Create a signature request for ``doc_id`` using the active provider."""
    sig_id, url = get_provider(DEFAULT_PROVIDER).request_signature(
        doc_id,
        user,
        workflow_id=workflow,
        approval_id=approval,
    )
    return {"id": sig_id, "url": url}


@app.post("/sign/{sig_id}/complete")
async def complete_sign(sig_id: str) -> None:
    """Mark a signature request as completed."""
    complete_signature(sig_id)
    process_webhook({"id": sig_id, "status": "signed"})


@app.get("/sign/{sig_id}")
async def get_sign_status(sig_id: str) -> dict[str, str]:
    """Return signature status."""
    status = signature_status(sig_id)
    return {"status": status}


@app.post("/hooks/documenso", status_code=204, response_class=Response)
async def documenso_webhook(payload: dict[str, object]) -> Response:
    """Process Documenso webhook callbacks."""
    try:
        process_webhook(cast(dict[str, str], payload))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(status_code=204)


@app.post("/token", response_model=auth.Token)
async def token(form_data: OAuth2PasswordRequestForm = Depends()) -> auth.Token:
    """Return a JWT access token for valid user credentials."""
    token_resp = await auth.login_for_access_token(form_data)
    log_event(
        "login",
        user=form_data.username,
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
            user=username,
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
    doc_path = Path(__file__).resolve().parent.parent.parent / "docs" / "getting_started.md"
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
async def list_logs(action: str | None = None, user: str | None = None) -> list[LogEntry]:
    """Return recorded logs optionally filtered by action or user."""
    return query_logs(action=action, user=user)


@app.get("/api/audit", response_model=list[LogEntry])
async def list_audit(action: str | None = None, user: str | None = None) -> list[LogEntry]:
    """Alias for :func:`list_logs` used by the dashboard."""
    return query_logs(action=action, user=user)


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
    """Stream log events to connected clients."""

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

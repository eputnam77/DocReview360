"""FastAPI application exposing DocuFlow endpoints."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from . import auth, reporting
from . import search as search_mod
from .ai_assist import rewrite_text, summarize_text
from .approvals import (
    ApprovalModel,
    create_approval,
    get_approval,
    list_approvals,
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
from .comments import CommentModel, add_comment, list_comments
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
    request_signature,
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
from .exporter import export_document
from .logs import LogEntry, log_event, query_logs
from .plugins import load_plugins
from .plugins import registry as plugin_registry
from .rbac import require_role
from .reporting import (
    DashboardEntry,
    SummaryReport,
    dashboard_data,
    generate_summary,
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
)
from .status import internal_status, public_status
from .workflows import (
    WorkflowModel,
    advance_workflow,
    assign_reviewer,
    create_workflow,
    get_workflow,
    workflows,
)


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


class ApprovalUpdate(BaseModel):
    """Input model for updating approval state."""

    state: str
    signature: str | None = None


class PluginModule(BaseModel):
    """Input model for registering plugins by module path."""

    module: str


class PluginToggle(BaseModel):
    """Input model for enabling or disabling a plugin."""

    name: str


class ProjectCreate(BaseModel):
    """Input model for creating projects."""

    id: str
    name: str
    user: str | None = None
    priority: int = 0


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


app = FastAPI(title="DocuFlow")

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@app.get("/projects", response_model=list[ProjectModel])
async def list_projects_endpoint() -> list[ProjectModel]:
    """Return all known projects."""
    return list_projects()


@app.post("/projects", status_code=201, response_model=ProjectModel)
async def create_project_endpoint(body: ProjectCreate) -> ProjectModel:
    """Create a new project."""
    project = ProjectModel(**body.model_dump())
    add_project(project)
    log_event("create_project", user=project.user, project=project.id)
    return project


@app.get("/projects/{project_id}", response_model=ProjectModel)
async def get_project_endpoint(project_id: str) -> ProjectModel:
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


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
    data = await file.read()
    document = import_document(
        file.filename,
        data,
        project=project,
        user=user,
        priority=priority,
    )
    log_event(
        "import_document",
        user=user,
        project=project,
        filename=file.filename,
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
    log_event("import_tiptap", document=document.id)
    return document


@app.get("/documents", response_model=list[DocumentModel])
async def list_documents_endpoint() -> list[DocumentModel]:
    """Return all imported documents."""
    return list_docs()


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
        return update_document(doc_id, document.content, priority=document.priority)
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
        data, media, filename = export_document(document, fmt)
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
    """Return documents matching a full text query."""
    return search(
        q,
        project=project,
        user=user,
        priority=priority,
        after=after,
        before=before,
    )


@app.get("/search/export")
async def export_search_results(q: str, fmt: str = "json") -> Response:
    """Return search results in JSON or CSV with ranking and snippets."""
    results = ranked_search(q)
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


@app.delete("/document-types/{name}", status_code=204, response_class=Response)
async def delete_document_type_endpoint(name: str) -> Response:
    """Remove an existing document type."""
    try:
        delete_document_type(name)
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
    return create_approval(body.workflow, body.reviewer)


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
        return update_approval_state(approval_id, body.state, signature=body.signature)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/approvals/{approval_id}/sign")
async def sign_approval_endpoint(approval_id: str) -> dict[str, str]:
    """Begin a Documenso signing flow for an approval."""
    approval = get_approval(approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    wf = get_workflow(approval.workflow)
    if wf is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return_to = f"/projects/{wf.project}"
    sig_id, url = request_signature(
        wf.project,
        approval.reviewer,
        workflow_id=approval.workflow,
        approval_id=approval.id,
        return_url=return_to,
    )
    approval.signature = sig_id
    return {"id": sig_id, "url": url}


@app.post("/sign/{doc_id}")
async def sign_document(
    doc_id: str,
    user: str = Form(...),
    workflow: str | None = Form(None),
    approval: str | None = Form(None),
) -> dict[str, str]:
    """Create a Documenso signature request for ``doc_id``.

    Returns both the signature ``id`` and a ``url`` that a client should
    redirect the user to for signing.
    """
    sig_id, url = request_signature(
        doc_id,
        user,
        workflow,
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
async def documenso_webhook(payload: dict) -> Response:
    """Process Documenso webhook callbacks."""
    try:
        process_webhook(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(status_code=204)


@app.post("/token", response_model=auth.Token)
async def token(form_data: OAuth2PasswordRequestForm = Depends()) -> auth.Token:
    """Return a JWT access token for valid user credentials."""
    token_resp = await auth.login_for_access_token(form_data)
    log_event("login", user=form_data.username)
    return token_resp


@app.post("/oidc/token", response_model=auth.Token)
async def oidc_token(form_data: OAuth2PasswordRequestForm = Depends()) -> auth.Token:
    """Return an ID token using the OIDC demonstration flow."""
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
        return templates.TemplateResponse("dashboard.html", {"request": request, "user": "admin"})
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, username: str = Form(...), password: str = Form(...)) -> Response:
    """Simple credential check for admin user."""
    if username == "admin" and password == "admin":
        response = RedirectResponse("/projects", status_code=303)
        response.set_cookie("session", "admin")
        log_event("login", user=username)
        return response
    return templates.TemplateResponse(
        "login.html", {"request": request, "error": "Invalid credentials"}, status_code=400
    )


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    """Placeholder dashboard displayed after login."""
    if request.cookies.get("session") != "admin":
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": "admin"})


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


@app.get("/reports/dashboard", response_model=list[DashboardEntry])
async def get_dashboard_data() -> list[DashboardEntry]:
    """Return per-project data for dashboard widgets."""
    return dashboard_data()


@app.get("/dashboard/widgets")
async def get_widget_counts() -> dict[str, int]:
    """Return assignment and approval counts for dashboard widgets."""
    return widget_counts()


@app.get("/status/public")
async def public_status_endpoint() -> dict[str, int]:
    """Expose limited status for unauthenticated users."""
    return public_status()


@app.get("/status/internal")
async def internal_status_endpoint() -> dict[str, int]:
    """Return extended system status for admins."""
    return internal_status()


@app.websocket("/ws/dashboard")
async def dashboard_stream(websocket: WebSocket) -> None:
    """Send dashboard data periodically over a websocket."""
    await websocket.accept()
    try:
        while True:
            data = [entry.model_dump() for entry in dashboard_data()]
            await websocket.send_json(data)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass

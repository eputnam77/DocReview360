"""FastAPI application exposing DocuFlow endpoints."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from . import auth
from .doc_types import (
    DocumentTypeModel,
    add_document_type,
    delete_document_type,
    get_document_type,
    list_document_types,
    update_document_type,
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
from .search import ProjectModel, list_projects, search
from .workflows import (
    WorkflowModel,
    advance_workflow,
    assign_reviewer,
    create_workflow,
    get_workflow,
)


class WorkflowCreate(BaseModel):
    """Input model for creating workflows."""

    project: str
    phases: list[str]


class ReviewerAssign(BaseModel):
    """Input model for assigning reviewers."""

    user: str


app = FastAPI(title="DocuFlow")

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@app.get("/projects", response_model=list[ProjectModel])
async def list_projects_endpoint() -> list[ProjectModel]:
    """Return all known projects."""
    return list_projects()


@app.post("/documents/import", status_code=201, response_model=DocumentModel)
async def import_document_endpoint(
    file: UploadFile = File(...),
    project: str | None = Form(None),
    user: str | None = Form(None),
    priority: int | None = Form(None),
) -> DocumentModel:
    """Import a DOCX or Markdown file and store it as a document."""
    data = await file.read()
    return import_document(
        file.filename,
        data,
        project=project,
        user=user,
        priority=priority,
    )


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


@app.post("/document-types", status_code=201, response_model=DocumentTypeModel)
async def create_document_type(doc_type: DocumentTypeModel) -> DocumentTypeModel:
    """Create a new document type."""
    add_document_type(doc_type)
    return doc_type


@app.get("/document-types", response_model=list[DocumentTypeModel])
async def get_document_types() -> list[DocumentTypeModel]:
    """Return all configured document types."""
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


@app.post("/token", response_model=auth.Token)
async def token(form_data: OAuth2PasswordRequestForm = Depends()) -> auth.Token:
    """Return a JWT access token for valid user credentials."""
    return await auth.login_for_access_token(form_data)


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
        response = RedirectResponse("/dashboard", status_code=303)
        response.set_cookie("session", "admin")
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

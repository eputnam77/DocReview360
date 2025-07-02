"""FastAPI application exposing DocuFlow endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates

from . import auth
from .doc_types import (
    DocumentTypeModel,
    add_document_type,
    get_document_type,
    list_document_types,
)

app = FastAPI(title="DocuFlow")

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@app.get("/projects")
async def list_projects() -> list[dict[str, str]]:
    """Return placeholder project data."""
    return [{"id": "1", "name": "Example"}]


@app.get("/documents")
async def list_documents() -> list[dict[str, str]]:
    """Return placeholder document data."""
    return [{"id": "1", "project_id": "1"}]


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

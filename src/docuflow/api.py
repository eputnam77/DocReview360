"""FastAPI application exposing DocuFlow endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

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

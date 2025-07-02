"""FastAPI application exposing DocuFlow endpoints."""

from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="DocuFlow")


@app.get("/projects")
async def list_projects() -> list[dict[str, str]]:
    """Return placeholder project data."""
    return [{"id": "1", "name": "Example"}]


@app.get("/documents")
async def list_documents() -> list[dict[str, str]]:
    """Return placeholder document data."""
    return [{"id": "1", "project_id": "1"}]

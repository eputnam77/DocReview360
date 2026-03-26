# SPDX-License-Identifier: MIT
"""Document types sub-router — /document-types/* endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from pydantic import BaseModel

from .. import auth
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
from ..rbac import require_role
from ..search import list_projects, update_project

router = APIRouter()


class _PhasesUpdateRequest(BaseModel):
    phases: list[str]


# ---------------------------------------------------------------------------
# Document type routes
# ---------------------------------------------------------------------------


@router.post("/document-types", status_code=201, response_model=DocumentTypeModel)
async def create_document_type(
    doc_type: DocumentTypeModel,
    _user: auth.User = Depends(require_role("admin")),
) -> DocumentTypeModel:
    """Create a new document type (admin only)."""
    try:
        if not doc_type.workflow:
            from ..doc_types import DEFAULT_DOC_TYPE_PHASES
            workflow = DEFAULT_DOC_TYPE_PHASES.get(doc_type.name, ["Draft Development"])
            doc_type = doc_type.model_copy(update={"workflow": workflow})
        add_document_type(doc_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return doc_type


@router.get("/document-types", response_model=list[DocumentTypeModel])
async def get_document_types(
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[DocumentTypeModel]:
    """Return all configured document types."""
    return list_document_types()


@router.get("/document-types/export")
async def export_doc_types_endpoint(
    _user: auth.User = Depends(require_role("admin")),
) -> Response:
    """Download all document types as JSON (admin only)."""
    data = export_document_types_json()
    headers = {"Content-Disposition": "attachment; filename=document_types.json"}
    return Response(content=data, media_type="application/json", headers=headers)


@router.post("/document-types/import", status_code=201, response_model=list[DocumentTypeModel])
async def import_doc_types_endpoint(
    file: UploadFile = File(...),
    _user: auth.User = Depends(require_role("admin")),
) -> list[DocumentTypeModel]:
    """Upload a JSON file of document types and replace existing ones (admin only)."""
    data = await file.read()
    try:
        import_document_types_json(data.decode())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return list_document_types()


@router.get("/document-types/{name}", response_model=DocumentTypeModel)
async def get_document_type_endpoint(
    name: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> DocumentTypeModel:
    """Retrieve a single document type by name."""
    doc_type = get_document_type(name)
    if doc_type is None:
        raise HTTPException(status_code=404, detail="Document type not found")
    return doc_type


@router.put("/document-types/{name}", response_model=DocumentTypeModel)
async def update_document_type_endpoint(
    name: str,
    doc_type: DocumentTypeModel,
    _user: auth.User = Depends(require_role("admin")),
) -> DocumentTypeModel:
    """Replace an existing document type (admin only)."""
    try:
        if not doc_type.workflow:
            existing = get_document_type(name)
            if existing is None:
                raise KeyError(f"Document type '{name}' not found")
            doc_type = doc_type.model_copy(update={"workflow": list(existing.workflow)})
        return update_document_type(name, doc_type)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/document-types/{name}/starter-content")
async def get_document_type_starter_content(
    name: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """Return the curated starter HTML template for a document type.

    The frontend editor calls this endpoint when creating a new blank document
    to pre-populate the TipTap editor with section headings and placeholder text
    appropriate for the chosen document type.
    """
    doc_type = get_document_type(name)
    if doc_type is None:
        raise HTTPException(status_code=404, detail=f"Document type '{name}' not found")
    return {"doc_type": name, "content": doc_type.template or f"<h1>{name}</h1>"}


@router.get("/document-types/{name}/phases", response_model=list[str])
async def get_document_type_phases(
    name: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[str]:
    """Return the ordered list of workflow phases configured for a document type."""
    doc_type = get_document_type(name)
    if doc_type is None:
        raise HTTPException(status_code=404, detail=f"Document type '{name}' not found")
    return list(doc_type.workflow)


@router.put("/document-types/{name}/phases", response_model=DocumentTypeModel)
async def update_document_type_phases(
    name: str,
    body: _PhasesUpdateRequest,
    _user: auth.User = Depends(require_role("admin")),
) -> DocumentTypeModel:
    """Replace the workflow phases for a document type (admin only).

    Phases must be non-empty strings.  The order of the list defines the
    review progression for documents of this type.  Returns HTTP 404 if
    the document type does not exist and HTTP 422 on invalid phase data.
    """
    existing = get_document_type(name)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Document type '{name}' not found")
    if not body.phases:
        raise HTTPException(status_code=422, detail="phases must contain at least one entry")
    for phase in body.phases:
        if not isinstance(phase, str) or not phase.strip():
            raise HTTPException(status_code=422, detail="Each phase must be a non-empty string")
    updated = existing.model_copy(update={"workflow": body.phases})
    try:
        return update_document_type(name, updated)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/document-types/{name}/usage", response_model=dict[str, Any])
async def check_document_type_usage_endpoint(
    name: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Check if a document type is in use and return usage information."""
    doc_type = get_document_type(name)
    if not doc_type:
        raise HTTPException(status_code=404, detail=f"Document type '{name}' not found")

    projects = list_projects()
    projects_using_doc_type = [p for p in projects if p.doc_type == name]

    return {
        "name": name,
        "in_use": len(projects_using_doc_type) > 0,
        "usage_count": len(projects_using_doc_type),
        "projects": [{"id": p.id, "name": p.name} for p in projects_using_doc_type],
    }


@router.delete(
    "/document-types/{name}", status_code=204, response_class=Response, response_model=None
)
async def delete_document_type_endpoint(
    name: str,
    replacement: str | None = None,
    _user: auth.User = Depends(require_role("admin")),
) -> Response:
    """Remove an existing document type (admin only). If in use, replacement is required."""
    doc_type = get_document_type(name)
    if not doc_type:
        raise HTTPException(status_code=404, detail=f"Document type '{name}' not found")

    projects = list_projects()
    projects_using_doc_type = [p for p in projects if p.doc_type == name]

    if projects_using_doc_type:
        if replacement:
            if replacement == name:
                raise HTTPException(
                    status_code=400, detail=f"Replacement document type '{replacement}' not found"
                )
            replacement_doc_type = get_document_type(replacement)
            if not replacement_doc_type:
                raise HTTPException(
                    status_code=404, detail=f"Replacement document type '{replacement}' not found"
                )
            for project in projects_using_doc_type:
                update_project(project.id, doc_type=replacement)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Document type '{name}' is in use. Please specify a replacement.",
            )

    try:
        delete_document_type(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return Response(status_code=204)

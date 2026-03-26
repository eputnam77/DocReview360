# SPDX-License-Identifier: MIT
"""Hierarchical configuration, custom workflows, and custom fields API endpoints."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import auth
from ..custom_fields import (
    create_field_definition,
    delete_field_definition,
    get_field_values,
    list_field_definitions,
    set_field_value,
    validate_field_value,
)
from ..custom_workflows import (
    create_custom_workflow,
    delete_custom_workflow,
    get_custom_workflow,
    list_custom_workflows,
    update_custom_workflow,
)
from ..db_store import get_db
from ..hierarchical_config import (
    SYSTEM_DEFAULTS,
    delete_org_config,
    delete_project_config,
    get_org_config_all,
    get_project_config_all,
    set_org_config,
    set_project_config,
)
from ..rbac import require_role

router = APIRouter(tags=["configuration"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class ConfigValuePayload(BaseModel):
    value: Any


class CustomWorkflowCreate(BaseModel):
    name: str
    steps: list[dict[str, Any]]
    description: str | None = None
    doc_types: list[str] | None = None


class CustomWorkflowUpdate(BaseModel):
    steps: list[dict[str, Any]] | None = None
    description: str | None = None
    doc_types: list[str] | None = None
    is_active: bool | None = None


class CustomFieldCreate(BaseModel):
    entity_type: str
    field_name: str
    field_label: str
    field_type: str
    options: list[str] | None = None
    required: bool = False
    default_value: Any = None
    sort_order: int = 0


def _defn_to_dict(defn: Any) -> dict[str, Any]:
    return {
        "id": defn.id,
        "org_id": defn.org_id,
        "entity_type": defn.entity_type,
        "field_name": defn.field_name,
        "field_label": defn.field_label,
        "field_type": defn.field_type,
        "options": json.loads(defn.options) if defn.options else None,
        "required": defn.required,
        "default_value": json.loads(defn.default_value) if defn.default_value else None,
        "sort_order": defn.sort_order,
        "is_active": defn.is_active,
    }


def _wf_to_dict(wf: Any) -> dict[str, Any]:
    return {
        "id": wf.id,
        "org_id": wf.org_id,
        "name": wf.name,
        "description": wf.description,
        "steps": json.loads(wf.steps),
        "doc_types": json.loads(wf.doc_types) if wf.doc_types else None,
        "created_by": wf.created_by,
        "created_at": wf.created_at.isoformat() if wf.created_at else None,
        "is_active": wf.is_active,
    }


# ---------------------------------------------------------------------------
# Hierarchical config endpoints
# ---------------------------------------------------------------------------


@router.get("/config/system")
async def get_system_config(
    current_user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Return system-level config defaults (admin only)."""
    return SYSTEM_DEFAULTS


@router.get("/config/org/{org_id}")
async def get_org_config(
    org_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Return merged config for an organization."""
    with get_db().orm_session() as db:
        return get_org_config_all(db, org_id)


@router.put("/config/org/{org_id}/{key:path}")
async def set_org_config_endpoint(
    org_id: str,
    key: str,
    payload: ConfigValuePayload,
    current_user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Set an org-level config override (admin only)."""
    with get_db().orm_session() as db:
        row = set_org_config(db, org_id, key, payload.value, updated_by=current_user.username)
        return {"org_id": org_id, "key": key, "value": payload.value}


@router.delete("/config/org/{org_id}/{key:path}")
async def delete_org_config_endpoint(
    org_id: str,
    key: str,
    current_user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Delete an org-level config override, reverting to system default (admin only)."""
    with get_db().orm_session() as db:
        deleted = delete_org_config(db, org_id, key)
        if not deleted:
            raise HTTPException(status_code=404, detail="Config key not found for this org")
        return {"deleted": True, "org_id": org_id, "key": key}


@router.get("/config/project/{project_id}")
async def get_project_config(
    project_id: str,
    org_id: str | None = None,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Return merged config for a project (system → org → project)."""
    with get_db().orm_session() as db:
        return get_project_config_all(db, project_id, org_id=org_id)


@router.put("/config/project/{project_id}/{key:path}")
async def set_project_config_endpoint(
    project_id: str,
    key: str,
    payload: ConfigValuePayload,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Set a project-level config override."""
    with get_db().orm_session() as db:
        set_project_config(db, project_id, key, payload.value, updated_by=current_user.username)
        return {"project_id": project_id, "key": key, "value": payload.value}


@router.delete("/config/project/{project_id}/{key:path}")
async def delete_project_config_endpoint(
    project_id: str,
    key: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Delete a project-level config override."""
    with get_db().orm_session() as db:
        deleted = delete_project_config(db, project_id, key)
        if not deleted:
            raise HTTPException(status_code=404, detail="Config key not found for this project")
        return {"deleted": True, "project_id": project_id, "key": key}


# ---------------------------------------------------------------------------
# Custom workflow endpoints
# ---------------------------------------------------------------------------


@router.get("/orgs/{org_id}/workflows")
async def list_org_workflows(
    org_id: str,
    doc_type: str | None = None,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[dict[str, Any]]:
    """List custom workflow templates for an organization."""
    with get_db().orm_session() as db:
        workflows = list_custom_workflows(db, org_id, doc_type=doc_type)
        return [_wf_to_dict(w) for w in workflows]


@router.post("/orgs/{org_id}/workflows")
async def create_org_workflow(
    org_id: str,
    payload: CustomWorkflowCreate,
    current_user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Create a custom workflow template for an organization (admin only)."""
    with get_db().orm_session() as db:
        try:
            wf = create_custom_workflow(
                db,
                org_id=org_id,
                name=payload.name,
                steps=payload.steps,
                description=payload.description,
                doc_types=payload.doc_types,
                created_by=current_user.username,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return _wf_to_dict(wf)


@router.get("/orgs/{org_id}/workflows/{name}")
async def get_org_workflow(
    org_id: str,
    name: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Get a specific custom workflow template."""
    with get_db().orm_session() as db:
        wf = get_custom_workflow(db, org_id, name)
        if wf is None:
            raise HTTPException(status_code=404, detail="Custom workflow not found")
        return _wf_to_dict(wf)


@router.put("/orgs/{org_id}/workflows/{name}")
async def update_org_workflow(
    org_id: str,
    name: str,
    payload: CustomWorkflowUpdate,
    current_user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Update a custom workflow template (admin only)."""
    updates = payload.model_dump(exclude_none=True)
    with get_db().orm_session() as db:
        try:
            wf = update_custom_workflow(db, org_id, name, **updates)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return _wf_to_dict(wf)


@router.delete("/orgs/{org_id}/workflows/{name}")
async def delete_org_workflow(
    org_id: str,
    name: str,
    current_user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Delete a custom workflow template (admin only)."""
    with get_db().orm_session() as db:
        deleted = delete_custom_workflow(db, org_id, name)
        if not deleted:
            raise HTTPException(status_code=404, detail="Custom workflow not found")
        return {"deleted": True}


# ---------------------------------------------------------------------------
# Custom field endpoints
# ---------------------------------------------------------------------------


@router.get("/orgs/{org_id}/fields")
async def list_org_fields(
    org_id: str,
    entity_type: str | None = None,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[dict[str, Any]]:
    """List custom field definitions for an organization."""
    with get_db().orm_session() as db:
        defns = list_field_definitions(db, org_id, entity_type=entity_type)
        return [_defn_to_dict(d) for d in defns]


@router.post("/orgs/{org_id}/fields")
async def create_org_field(
    org_id: str,
    payload: CustomFieldCreate,
    current_user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Create a custom field definition (admin only)."""
    with get_db().orm_session() as db:
        try:
            defn = create_field_definition(
                db,
                org_id=org_id,
                entity_type=payload.entity_type,
                field_name=payload.field_name,
                field_label=payload.field_label,
                field_type=payload.field_type,
                options=payload.options,
                required=payload.required,
                default_value=payload.default_value,
                sort_order=payload.sort_order,
                created_by=current_user.username,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return _defn_to_dict(defn)


@router.delete("/orgs/{org_id}/fields/{field_id}")
async def delete_org_field(
    org_id: str,
    field_id: str,
    current_user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Soft-delete a custom field definition (admin only)."""
    with get_db().orm_session() as db:
        deleted = delete_field_definition(db, org_id, field_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Field definition not found")
        return {"deleted": True}


@router.get("/documents/{doc_id}/custom-fields")
async def get_document_custom_fields(
    doc_id: str,
    org_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Get custom field values for a document."""
    with get_db().orm_session() as db:
        values = get_field_values(db, entity_id=doc_id, org_id=org_id, entity_type="document")
        return {"document_id": doc_id, "fields": values}


@router.put("/documents/{doc_id}/custom-fields")
async def set_document_custom_fields(
    doc_id: str,
    org_id: str,
    fields: dict[str, Any],
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Set custom field values for a document."""
    with get_db().orm_session() as db:
        defns = list_field_definitions(db, org_id, entity_type="document")
        defn_map = {d.field_name: d for d in defns}
        errors = {}
        for field_name, value in fields.items():
            defn = defn_map.get(field_name)
            if defn is None:
                errors[field_name] = "Field not defined for this org"
                continue
            err = validate_field_value(defn, value)
            if err:
                errors[field_name] = err
        if errors:
            raise HTTPException(status_code=422, detail=errors)
        for field_name, value in fields.items():
            defn = defn_map.get(field_name)
            if defn:
                set_field_value(db, defn.id, doc_id, value, updated_by=current_user.username)
        return {"document_id": doc_id, "updated": list(fields.keys())}


@router.get("/projects/{project_id}/custom-fields")
async def get_project_custom_fields(
    project_id: str,
    org_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Get custom field values for a project."""
    with get_db().orm_session() as db:
        values = get_field_values(db, entity_id=project_id, org_id=org_id, entity_type="project")
        return {"project_id": project_id, "fields": values}


@router.put("/projects/{project_id}/custom-fields")
async def set_project_custom_fields(
    project_id: str,
    org_id: str,
    fields: dict[str, Any],
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Set custom field values for a project."""
    with get_db().orm_session() as db:
        defns = list_field_definitions(db, org_id, entity_type="project")
        defn_map = {d.field_name: d for d in defns}
        errors = {}
        for field_name, value in fields.items():
            defn = defn_map.get(field_name)
            if defn is None:
                errors[field_name] = "Field not defined for this org"
                continue
            err = validate_field_value(defn, value)
            if err:
                errors[field_name] = err
        if errors:
            raise HTTPException(status_code=422, detail=errors)
        for field_name, value in fields.items():
            defn = defn_map.get(field_name)
            if defn:
                set_field_value(db, defn.id, project_id, value, updated_by=current_user.username)
        return {"project_id": project_id, "updated": list(fields.keys())}

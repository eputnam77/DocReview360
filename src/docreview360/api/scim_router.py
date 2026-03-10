# SPDX-License-Identifier: MIT
"""SCIM 2.0 Service Provider endpoints for user and group lifecycle management."""

from __future__ import annotations

import os
import secrets
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .. import auth, rbac

router = APIRouter(prefix="/scim/v2", tags=["scim"])

_SCIM_USER_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:User"
_SCIM_GROUP_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:Group"
_SCIM_LIST_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:ListResponse"
_SCIM_PATCH_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:PatchOp"
_SCIM_ERROR_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:Error"

_KNOWN_ROLES = ["admin", "auditor", "reviewer", "viewer", "editor"]


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------


def _require_scim_auth(request: Request) -> None:
    """Validate SCIM Bearer token. Raises 404 if SCIM is not configured."""
    expected = os.getenv("DOCREVIEW360_SCIM_BEARER_TOKEN", "").strip()
    if not expected:
        raise HTTPException(status_code=404, detail="SCIM provisioning is not enabled")
    auth_header = request.headers.get("Authorization", "")
    x_token = request.headers.get("X-SCIM-Token", "")
    provided = ""
    if auth_header.startswith("Bearer "):
        provided = auth_header[7:].strip()
    elif x_token:
        provided = x_token.strip()
    if not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Invalid SCIM bearer token")


# ---------------------------------------------------------------------------
# SCIM resource helpers
# ---------------------------------------------------------------------------


def _user_to_scim(record: auth.UserRecord, base_url: str = "") -> dict[str, Any]:
    return {
        "schemas": [_SCIM_USER_SCHEMA],
        "id": record.username,
        "userName": record.username,
        "active": record.active,
        "meta": {
            "resourceType": "User",
            "location": f"{base_url}/scim/v2/Users/{record.username}",
        },
    }


def _group_to_scim(role_name: str, members: list[str], base_url: str = "") -> dict[str, Any]:
    return {
        "schemas": [_SCIM_GROUP_SCHEMA],
        "id": role_name,
        "displayName": role_name,
        "members": [{"value": m, "display": m} for m in members],
        "meta": {
            "resourceType": "Group",
            "location": f"{base_url}/scim/v2/Groups/{role_name}",
        },
    }


def _list_response(resources: list[dict], total: int | None = None) -> dict[str, Any]:
    return {
        "schemas": [_SCIM_LIST_SCHEMA],
        "totalResults": total if total is not None else len(resources),
        "startIndex": 1,
        "itemsPerPage": len(resources),
        "Resources": resources,
    }


def _base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


# ---------------------------------------------------------------------------
# Pydantic models for request bodies
# ---------------------------------------------------------------------------


class ScimUserCreate(BaseModel):
    userName: str
    active: bool = True
    schemas: list[str] = [_SCIM_USER_SCHEMA]


class ScimPatchOp(BaseModel):
    schemas: list[str] = [_SCIM_PATCH_SCHEMA]
    Operations: list[dict[str, Any]] = []


# ---------------------------------------------------------------------------
# User endpoints
# ---------------------------------------------------------------------------


@router.get("/Users")
def scim_list_users(
    request: Request,
    filter: str | None = None,
    _: None = Depends(_require_scim_auth),
) -> dict:
    """List all users, with optional ``?filter=userName eq "alice"`` support."""
    repo = auth._get_user_repository()
    all_records = repo.list_users()

    # Basic filter: userName eq "value"
    if filter:
        import re
        m = re.match(r'userName\s+eq\s+"([^"]+)"', filter.strip(), re.IGNORECASE)
        if m:
            target = m.group(1)
            all_records = [r for r in all_records if r.username == target]

    base = _base_url(request)
    resources = [_user_to_scim(r, base) for r in all_records]
    return _list_response(resources)


@router.post("/Users", status_code=201)
def scim_create_user(
    request: Request,
    body: ScimUserCreate,
    _: None = Depends(_require_scim_auth),
) -> dict:
    """Create a new user via SCIM provisioning."""
    repo = auth._get_user_repository()
    if repo.get_user(body.userName):
        raise HTTPException(status_code=409, detail=f"User {body.userName!r} already exists")
    try:
        repo._seed_user(body.userName, secrets.token_hex(32), active=body.active)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    record = repo.get_user(body.userName)
    if record is None:
        raise HTTPException(status_code=500, detail="User creation failed")
    try:
        from ..logs import log_event
        log_event("scim_user_create", user_id=body.userName)
    except Exception:
        pass
    return _user_to_scim(record, _base_url(request))


@router.get("/Users/{user_id}")
def scim_get_user(
    user_id: str,
    request: Request,
    _: None = Depends(_require_scim_auth),
) -> dict:
    """Get a single user by ID (username)."""
    repo = auth._get_user_repository()
    record = repo.get_user(user_id)
    if record is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_to_scim(record, _base_url(request))


@router.put("/Users/{user_id}")
def scim_replace_user(
    user_id: str,
    request: Request,
    body: ScimUserCreate,
    _: None = Depends(_require_scim_auth),
) -> dict:
    """Replace user attributes (active state only for now)."""
    repo = auth._get_user_repository()
    record = repo.get_user(user_id)
    if record is None:
        raise HTTPException(status_code=404, detail="User not found")
    repo.set_active(user_id, body.active)
    updated = repo.get_user(user_id) or record
    try:
        from ..logs import log_event
        log_event("scim_user_replace", user_id=user_id, active=body.active)
    except Exception:
        pass
    return _user_to_scim(updated, _base_url(request))


@router.patch("/Users/{user_id}")
def scim_patch_user(
    user_id: str,
    request: Request,
    body: ScimPatchOp,
    _: None = Depends(_require_scim_auth),
) -> dict:
    """Partial update of user attributes via SCIM PatchOp."""
    repo = auth._get_user_repository()
    record = repo.get_user(user_id)
    if record is None:
        raise HTTPException(status_code=404, detail="User not found")

    for op in body.Operations:
        operation = str(op.get("op", "")).lower()
        path = str(op.get("path", ""))
        value = op.get("value")

        if operation == "replace":
            if path == "active" and isinstance(value, bool):
                repo.set_active(user_id, value)
            elif not path and isinstance(value, dict):
                # Replace by attribute map
                if "active" in value:
                    repo.set_active(user_id, bool(value["active"]))

    updated = repo.get_user(user_id) or record
    try:
        from ..logs import log_event
        log_event("scim_user_patch", user_id=user_id)
    except Exception:
        pass
    return _user_to_scim(updated, _base_url(request))


@router.delete("/Users/{user_id}", status_code=204)
def scim_delete_user(
    user_id: str,
    _: None = Depends(_require_scim_auth),
) -> Response:
    """Delete a user via SCIM provisioning."""
    repo = auth._get_user_repository()
    removed = repo.delete_user(user_id)
    if not removed:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        from ..logs import log_event
        log_event("scim_user_delete", user_id=user_id)
    except Exception:
        pass
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Group endpoints (roles as SCIM groups)
# ---------------------------------------------------------------------------


def _all_roles() -> list[str]:
    """Return the known roles union any roles currently assigned in RBAC."""
    known = set(_KNOWN_ROLES)
    try:
        from ..auth import _get_user_repository
        repo = _get_user_repository()
        for user in repo.list_users():
            known.update(rbac.get_roles(user.username))
    except Exception:
        pass
    return sorted(known)


@router.get("/Groups")
def scim_list_groups(
    request: Request,
    _: None = Depends(_require_scim_auth),
) -> dict:
    """List all roles as SCIM Groups."""
    base = _base_url(request)
    roles = _all_roles()
    resources = [_group_to_scim(role, [], base) for role in roles]
    return _list_response(resources)


@router.get("/Groups/{group_id}")
def scim_get_group(
    group_id: str,
    request: Request,
    _: None = Depends(_require_scim_auth),
) -> dict:
    """Return a SCIM Group with its current members."""
    base = _base_url(request)
    if group_id not in _all_roles():
        raise HTTPException(status_code=404, detail="Group not found")
    try:
        from ..auth import _get_user_repository
        repo = _get_user_repository()
        members = [u.username for u in repo.list_users() if rbac.has_role(u.username, group_id)]
    except Exception:
        members = []
    return _group_to_scim(group_id, members, base)


# ---------------------------------------------------------------------------
# Service Provider Config + Schemas
# ---------------------------------------------------------------------------


@router.get("/ServiceProviderConfig")
def scim_service_provider_config(_: None = Depends(_require_scim_auth)) -> dict:
    """Return SCIM 2.0 Service Provider Configuration."""
    return {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"],
        "patch": {"supported": True},
        "bulk": {"supported": False, "maxOperations": 0, "maxPayloadSize": 0},
        "filter": {"supported": True, "maxResults": 200},
        "changePassword": {"supported": False},
        "sort": {"supported": False},
        "etag": {"supported": False},
        "authenticationSchemes": [
            {
                "type": "oauthbearertoken",
                "name": "Bearer Token",
                "description": "Bearer token issued at DOCREVIEW360_SCIM_BEARER_TOKEN",
            }
        ],
    }


@router.get("/Schemas")
def scim_schemas(_: None = Depends(_require_scim_auth)) -> dict:
    """Return SCIM 2.0 schema definitions."""
    return _list_response(
        [
            {
                "id": _SCIM_USER_SCHEMA,
                "name": "User",
                "description": "User account",
                "attributes": [
                    {"name": "userName", "type": "string", "required": True},
                    {"name": "active", "type": "boolean", "required": False},
                ],
            },
            {
                "id": _SCIM_GROUP_SCHEMA,
                "name": "Group",
                "description": "Role / group",
                "attributes": [
                    {"name": "displayName", "type": "string", "required": True},
                    {"name": "members", "type": "complex", "required": False},
                ],
            },
        ]
    )

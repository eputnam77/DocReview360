# SPDX-License-Identifier: MIT
"""Organizations sub-router: multi-tenant org management endpoints.

Routes:
    GET  /organizations                       -- list all orgs (admin)
    POST /organizations                       -- create org (admin)
    GET  /organizations/{org_id}              -- get org (admin or member)
    PUT  /organizations/{org_id}              -- update org (admin)
    DELETE /organizations/{org_id}            -- delete org (admin)
    GET  /organizations/{org_id}/settings     -- get org settings (admin)
    PUT  /organizations/{org_id}/settings     -- update org settings (admin)
    POST /organizations/{org_id}/users/{username}   -- assign user to org (admin)
    DELETE /organizations/{org_id}/users/{username} -- remove user from org (admin)
    GET  /organizations/{org_id}/users        -- list org users (admin or member)
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from .. import auth
from ..rbac import require_role, has_role
from ..organizations import (
    OrganizationSettings,
    assign_user_to_org,
    create_organization,
    delete_organization,
    get_org_settings,
    get_organization,
    get_user_org,
    list_org_users,
    list_organizations,
    remove_user_from_org,
    update_org_settings,
    update_organization,
)

_logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic request/response models
# ---------------------------------------------------------------------------


class OrgCreatePayload(BaseModel):
    """Payload for creating a new organization."""

    name: str
    settings: OrganizationSettings | None = None


class OrgUpdatePayload(BaseModel):
    """Payload for updating an existing organization."""

    name: str | None = None
    settings: OrganizationSettings | None = None


class OrgResponse(BaseModel):
    """Response schema for organization endpoints."""

    id: int
    name: str
    settings: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Authorization helpers
# ---------------------------------------------------------------------------


def _is_admin(user: auth.User) -> bool:
    return has_role(user.username, "admin")


def _require_admin_or_member(org_id: int, user: auth.User) -> None:
    """Raise HTTP 403 if ``user`` is neither admin nor a member of ``org_id``."""
    if _is_admin(user):
        return
    try:
        org = get_user_org(username=user.username)
    except Exception as exc:
        _logger.warning("Could not resolve user org for '%s': %s", user.username, exc)
        raise HTTPException(status_code=403, detail="Forbidden") from exc
    if org is None or org.get("id") != org_id:
        raise HTTPException(status_code=403, detail="Forbidden")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/organizations", response_model=list[OrgResponse])
async def list_orgs_endpoint(
    current_user: auth.User = Depends(require_role("admin")),
) -> list[dict[str, Any]]:
    """Return all organizations (admin only)."""
    try:
        return list_organizations()
    except Exception as exc:
        _logger.error("Failed to list organizations: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to list organizations") from exc


@router.post("/organizations", response_model=OrgResponse, status_code=201)
async def create_org_endpoint(
    body: OrgCreatePayload,
    current_user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Create a new organization (admin only)."""
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Organization name is required")
    try:
        return create_organization(name=name, settings=body.settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        _logger.error("Failed to create organization '%s': %s", name, exc)
        raise HTTPException(status_code=500, detail="Failed to create organization") from exc


@router.get("/organizations/{org_id}", response_model=OrgResponse)
async def get_org_endpoint(
    org_id: int,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Return a single organization (admin or org member)."""
    _require_admin_or_member(org_id, current_user)
    try:
        return get_organization(org_id=org_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        _logger.error("Failed to get organization %d: %s", org_id, exc)
        raise HTTPException(status_code=500, detail="Failed to retrieve organization") from exc


@router.put("/organizations/{org_id}", response_model=OrgResponse)
async def update_org_endpoint(
    org_id: int,
    body: OrgUpdatePayload,
    current_user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Update name and/or settings for an organization (admin only)."""
    try:
        return update_organization(
            org_id=org_id,
            name=body.name,
            settings=body.settings,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        _logger.error("Failed to update organization %d: %s", org_id, exc)
        raise HTTPException(status_code=500, detail="Failed to update organization") from exc


@router.delete("/organizations/{org_id}", status_code=204, response_class=Response)
async def delete_org_endpoint(
    org_id: int,
    current_user: auth.User = Depends(require_role("admin")),
) -> Response:
    """Delete an organization and disassociate its users (admin only)."""
    try:
        delete_organization(org_id=org_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        _logger.error("Failed to delete organization %d: %s", org_id, exc)
        raise HTTPException(status_code=500, detail="Failed to delete organization") from exc
    return Response(status_code=204)


@router.get("/organizations/{org_id}/settings", response_model=OrganizationSettings)
async def get_org_settings_endpoint(
    org_id: int,
    current_user: auth.User = Depends(require_role("admin")),
) -> OrganizationSettings:
    """Return per-organization settings (admin only)."""
    try:
        return get_org_settings(org_id=org_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        _logger.error("Failed to get settings for organization %d: %s", org_id, exc)
        raise HTTPException(status_code=500, detail="Failed to retrieve settings") from exc


@router.put("/organizations/{org_id}/settings", response_model=OrganizationSettings)
async def update_org_settings_endpoint(
    org_id: int,
    body: OrganizationSettings,
    current_user: auth.User = Depends(require_role("admin")),
) -> OrganizationSettings:
    """Update per-organization settings (admin only)."""
    try:
        return update_org_settings(org_id=org_id, settings=body)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        _logger.error("Failed to update settings for organization %d: %s", org_id, exc)
        raise HTTPException(status_code=500, detail="Failed to update settings") from exc


@router.post("/organizations/{org_id}/users/{username}", status_code=200)
async def assign_user_to_org_endpoint(
    org_id: int,
    username: str,
    current_user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Assign a user to an organization (admin only)."""
    try:
        assign_user_to_org(username=username, org_id=org_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        _logger.error(
            "Failed to assign user '%s' to organization %d: %s", username, org_id, exc
        )
        raise HTTPException(status_code=500, detail="Failed to assign user") from exc
    return {"username": username, "org_id": org_id}


@router.delete("/organizations/{org_id}/users/{username}", status_code=200)
async def remove_user_from_org_endpoint(
    org_id: int,
    username: str,
    current_user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Remove a user from an organization (admin only)."""
    try:
        remove_user_from_org(username=username)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        _logger.error(
            "Failed to remove user '%s' from organization %d: %s", username, org_id, exc
        )
        raise HTTPException(status_code=500, detail="Failed to remove user") from exc
    return {"username": username, "org_id": org_id}


@router.get("/organizations/{org_id}/users")
async def list_org_users_endpoint(
    org_id: int,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[dict[str, Any]]:
    """List users belonging to an organization (admin or org member)."""
    _require_admin_or_member(org_id, current_user)
    try:
        return list_org_users(org_id=org_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        _logger.error("Failed to list users for organization %d: %s", org_id, exc)
        raise HTTPException(status_code=500, detail="Failed to list org users") from exc

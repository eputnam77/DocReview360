# SPDX-License-Identifier: MIT
"""RBAC permission management sub-router — /rbac/* endpoints."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .. import auth, rbac, settings_manager
from ..rbac import require_role

_logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class RolePermissionUpdate(BaseModel):
    """Payload for updating role permissions."""

    permissions: list[str] = Field(default_factory=list)


class RolePermissionSummary(BaseModel):
    """Role permission summary with default counts."""

    role: str
    permissions: list[str]
    count: int
    default_permissions: list[str]
    default_count: int
    is_default: bool


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _normalize_role_permission(value: str) -> str | None:
    cleaned = value.strip().lower()
    return cleaned if cleaned else None


def _update_role_permissions(role: str, permissions: list[str]) -> None:
    settings = settings_manager.load_settings(settings_manager.SETTINGS_FILE)
    rbac_cfg = settings.get("rbac")
    if not isinstance(rbac_cfg, dict):
        rbac_cfg = {}
    roles_cfg = rbac_cfg.get("roles")
    if not isinstance(roles_cfg, dict):
        roles_cfg = {}
    normalized = []
    for perm in permissions:
        if not isinstance(perm, str):
            continue
        cleaned = _normalize_role_permission(perm)
        if cleaned:
            normalized.append(cleaned)
    roles_cfg[role] = sorted(set(normalized))
    rbac_cfg["roles"] = roles_cfg
    settings_manager.update_setting("rbac", rbac_cfg, settings_manager.SETTINGS_FILE)
    rbac.reload_role_permissions(force=True)


# ---------------------------------------------------------------------------
# RBAC endpoints
# ---------------------------------------------------------------------------


@router.put("/rbac/role-permissions/{role}", response_model=RolePermissionSummary)
async def update_role_permissions_endpoint(
    role: str,
    body: RolePermissionUpdate,
    user: auth.User = Depends(require_role("admin")),
) -> RolePermissionSummary:
    """Update permissions for a role and persist overrides."""
    normalized_role = role.strip().lower()
    if not normalized_role:
        raise HTTPException(status_code=400, detail="Role required")
    _update_role_permissions(normalized_role, body.permissions)
    current = rbac.get_role_permissions()
    defaults = getattr(rbac, "_DEFAULT_ROLE_PERMISSIONS", {})
    perms = sorted(current.get(normalized_role, set()))
    default_perms = sorted(defaults.get(normalized_role, set()))
    return RolePermissionSummary(
        role=normalized_role,
        permissions=perms,
        count=len(perms),
        default_permissions=default_perms,
        default_count=len(default_perms),
        is_default=set(perms) == set(default_perms),
    )


@router.delete("/rbac/role-permissions/{role}", response_model=RolePermissionSummary)
async def reset_role_permissions_endpoint(
    role: str,
    user: auth.User = Depends(require_role("admin")),
) -> RolePermissionSummary:
    """Reset a role back to default permissions."""
    normalized_role = role.strip().lower()
    if not normalized_role:
        raise HTTPException(status_code=400, detail="Role required")
    defaults = getattr(rbac, "_DEFAULT_ROLE_PERMISSIONS", {})
    default_perms = sorted(defaults.get(normalized_role, set()))
    _update_role_permissions(normalized_role, default_perms)
    current = rbac.get_role_permissions()
    perms = sorted(current.get(normalized_role, set()))
    return RolePermissionSummary(
        role=normalized_role,
        permissions=perms,
        count=len(perms),
        default_permissions=default_perms,
        default_count=len(default_perms),
        is_default=set(perms) == set(default_perms),
    )


@router.get("/rbac/role-permissions", response_model=list[RolePermissionSummary])
async def list_role_permissions_endpoint(
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[RolePermissionSummary]:
    """Return role permissions with default counts for UI display."""
    current = rbac.get_role_permissions()
    defaults = getattr(rbac, "_DEFAULT_ROLE_PERMISSIONS", {})
    roles = sorted(set(defaults) | set(current))
    summaries: list[RolePermissionSummary] = []
    for role in roles:
        perms = sorted(current.get(role, set()))
        default_perms = sorted(defaults.get(role, set()))
        summaries.append(
            RolePermissionSummary(
                role=role,
                permissions=perms,
                count=len(perms),
                default_permissions=default_perms,
                default_count=len(default_perms),
                is_default=set(perms) == set(default_perms),
            )
        )
    return summaries


@router.get("/rbac/matrix", response_model=dict[str, Any])
async def role_permission_matrix_endpoint(
    current_user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Return the full role-to-permission matrix for visualization."""
    current = rbac.get_role_permissions()
    defaults = getattr(rbac, "_DEFAULT_ROLE_PERMISSIONS", {})
    all_roles = sorted(set(defaults) | set(current))
    all_permissions: list[str] = sorted(
        {perm for perms in current.values() for perm in perms}
        | {perm for perms in defaults.values() for perm in perms}
    )
    matrix: dict[str, dict[str, bool]] = {}
    for role in all_roles:
        role_perms = set(current.get(role, set()))
        matrix[role] = {perm: (perm in role_perms) for perm in all_permissions}
    return {
        "roles": all_roles,
        "permissions": all_permissions,
        "matrix": matrix,
        "total_roles": len(all_roles),
        "total_permissions": len(all_permissions),
    }

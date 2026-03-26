# SPDX-License-Identifier: MIT
"""Feature flag API endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .. import auth
from ..db_store import get_db
from ..feature_flags import BUILT_IN_FLAGS, delete_flag, is_flag_enabled, list_flags, set_flag
from ..rbac import require_role

router = APIRouter(tags=["feature-flags"])


class FlagPayload(BaseModel):
    flag_name: str
    enabled: bool
    org_id: str | None = None
    rollout_percentage: int = Field(default=100, ge=0, le=100)


@router.get("/feature-flags")
async def list_all_flags(
    org_id: str | None = None,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[dict[str, Any]]:
    """List all feature flags with their effective state."""
    with get_db().orm_session() as db:
        return list_flags(db, org_id=org_id, user_id=current_user.username)


@router.get("/feature-flags/org/{org_id}")
async def list_org_flags(
    org_id: str,
    current_user: auth.User = Depends(require_role("admin")),
) -> list[dict[str, Any]]:
    """List feature flags for a specific org (admin only)."""
    with get_db().orm_session() as db:
        return list_flags(db, org_id=org_id)


@router.get("/feature-flags/{flag_name}")
async def get_flag(
    flag_name: str,
    org_id: str | None = None,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Get the effective state of a single feature flag."""
    with get_db().orm_session() as db:
        enabled = is_flag_enabled(db, flag_name, org_id=org_id, user_id=current_user.username)
        return {
            "flag_name": flag_name,
            "enabled": enabled,
            "built_in_default": BUILT_IN_FLAGS.get(flag_name),
        }


@router.post("/feature-flags")
async def set_feature_flag(
    payload: FlagPayload,
    current_user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Create or update a feature flag (admin only)."""
    with get_db().orm_session() as db:
        flag = set_flag(
            db,
            flag_name=payload.flag_name,
            enabled=payload.enabled,
            org_id=payload.org_id,
            rollout_percentage=payload.rollout_percentage,
            created_by=current_user.username,
        )
        return {
            "flag_name": flag.flag_name,
            "enabled": flag.enabled,
            "org_id": flag.org_id,
            "rollout_percentage": flag.rollout_percentage,
        }


@router.delete("/feature-flags/{flag_name}")
async def reset_feature_flag(
    flag_name: str,
    org_id: str | None = None,
    current_user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Reset a feature flag to its built-in default (admin only)."""
    with get_db().orm_session() as db:
        deleted = delete_flag(db, flag_name, org_id=org_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Feature flag override not found")
        return {"reset": True, "flag_name": flag_name, "org_id": org_id}

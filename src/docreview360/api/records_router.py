# SPDX-License-Identifier: MIT
"""Records retention & lifecycle router — /projects/{id}/lifecycle, /records-package
(Item 44 Phase 7)."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from .. import auth
from ..project_lifecycle import (
    PROJECT_LIFECYCLE_STATUSES,
    VALID_TRANSITIONS,
    get_lifecycle,
    is_feedback_blocked,
    set_lifecycle,
    set_published_metadata,
)
from ..search import get_project

_logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------


class LifecycleTransitionBody(BaseModel):
    status: str


class PublishedMetadataBody(BaseModel):
    published_ref: Optional[str] = None
    published_at: Optional[str] = None    # ISO date string
    published_venue: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_project_or_404(project_id: str):
    p = get_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p


def _require_manage_access(project, current_user: auth.User) -> None:
    from .projects_router import _enforce_project_manage_access
    _enforce_project_manage_access(project, current_user)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/projects/{project_id}/lifecycle")
async def get_project_lifecycle(
    project_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """Return the current lifecycle status of a project."""
    _get_project_or_404(project_id)
    record = get_lifecycle(project_id)
    return record.model_dump(mode="json")


@router.post("/projects/{project_id}/lifecycle")
async def transition_project_lifecycle(
    project_id: str,
    body: LifecycleTransitionBody,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """Transition a project to a new lifecycle status.

    Only project managers / admins may advance the lifecycle.
    Valid statuses: draft → in_review → reviewed → ready_for_publication
                    → published → submitted_to_records → closed
    """
    project = _get_project_or_404(project_id)
    _require_manage_access(project, current_user)
    if body.status not in PROJECT_LIFECYCLE_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{body.status}'. Valid: {list(PROJECT_LIFECYCLE_STATUSES)}",
        )
    try:
        record = set_lifecycle(project_id, body.status, set_by=current_user.username)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return record.model_dump(mode="json")


@router.put("/projects/{project_id}/published-metadata")
async def update_published_metadata(
    project_id: str,
    body: PublishedMetadataBody,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """Record external publication details (Federal Register ref, date, venue).

    Sets or updates published_ref, published_at, and published_venue without
    changing the lifecycle status.
    """
    project = _get_project_or_404(project_id)
    _require_manage_access(project, current_user)
    record = set_published_metadata(
        project_id,
        published_ref=body.published_ref,
        published_at=body.published_at,
        published_venue=body.published_venue,
    )
    return record.model_dump(mode="json")


@router.get("/projects/{project_id}/lifecycle/feedback-blocked")
async def check_feedback_blocked(
    project_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """Return whether feedback submission is blocked for this project."""
    _get_project_or_404(project_id)
    return {"blocked": is_feedback_blocked(project_id)}


@router.get("/projects/{project_id}/records-package")
async def get_records_package(
    project_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> Response:
    """Generate and return the complete review record package as a ZIP download.

    The ZIP contains:
    - manifest.json (machine-readable, includes integrity_hash)
    - assignments.json, feedback.json, notifications.json
    - nara_metadata.json, document_versions.json

    Requires project manager / admin access.
    """
    project = _get_project_or_404(project_id)
    _require_manage_access(project, current_user)

    try:
        from ..records_package import generate_records_package
        manifest, zip_bytes = generate_records_package(project_id)
    except Exception as exc:
        _logger.error("Failed to generate records package for %s: %s", project_id, exc)
        raise HTTPException(
            status_code=500, detail="Failed to generate records package"
        ) from exc

    filename = f"records-{project_id}.zip"
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Content-Hash": f"sha256={manifest.integrity_hash}",
        },
    )

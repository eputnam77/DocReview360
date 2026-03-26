# SPDX-License-Identifier: MIT
"""SLA / deadline tracking router — /document-types/{name}/sla, /projects/{id}/sla-summary
(Item 44 Phase 8)."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import auth
from ..search import get_project
from ..sla_tracker import (
    get_deadline_status,
    get_sla_config,
    get_sla_summary,
    list_sla_configs,
    run_sla_reminders,
    set_sla_config,
)

_logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------


class SLAConfigBody(BaseModel):
    default_review_days: int = 14
    reminder_days_before: list[int] = [3, 1]
    escalation_threshold_days: int = 3
    phase: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_project_or_404(project_id: str):
    p = get_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p


def _require_admin(current_user: auth.User) -> None:
    from .projects_router import _is_admin_user
    if not _is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")


def _require_manage_access(project, current_user: auth.User) -> None:
    from .projects_router import _enforce_project_manage_access
    _enforce_project_manage_access(project, current_user)


# ---------------------------------------------------------------------------
# Endpoints — SLA config (per doc type)
# ---------------------------------------------------------------------------


@router.get("/document-types/{doc_type}/sla")
async def get_doc_type_sla(
    doc_type: str,
    phase: Optional[str] = None,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """Return the SLA configuration for a document type (and optional phase)."""
    config = get_sla_config(doc_type, phase=phase)
    return config.model_dump()


@router.put("/document-types/{doc_type}/sla")
async def set_doc_type_sla(
    doc_type: str,
    body: SLAConfigBody,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """Set (upsert) the SLA configuration for a document type."""
    _require_admin(current_user)
    config = set_sla_config(
        doc_type,
        phase=body.phase,
        default_review_days=body.default_review_days,
        reminder_days_before=body.reminder_days_before,
        escalation_threshold_days=body.escalation_threshold_days,
    )
    return config.model_dump()


@router.get("/document-types/sla/all")
async def list_all_sla_configs(
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[dict]:
    """Return all stored SLA configurations."""
    _require_admin(current_user)
    return [c.model_dump() for c in list_sla_configs()]


# ---------------------------------------------------------------------------
# Endpoints — SLA summary (per project)
# ---------------------------------------------------------------------------


@router.get("/projects/{project_id}/sla-summary")
async def get_project_sla_summary(
    project_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """Return SLA status summary for all active reviewer assignments on a project.

    Returns: total, on_track, due_soon, overdue, no_deadline, max_overdue_days.
    """
    project = _get_project_or_404(project_id)
    from .assignments_router import _require_project_access
    _require_project_access(project, current_user)
    summary = get_sla_summary(project_id)
    return summary.model_dump()


@router.get("/projects/{project_id}/sla-deadlines")
async def get_project_sla_deadlines(
    project_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[dict]:
    """Return per-assignment deadline status for a project."""
    project = _get_project_or_404(project_id)
    from .assignments_router import _require_project_access
    _require_project_access(project, current_user)
    from ..review_assignments import list_assignments
    assignments = list_assignments(project_id)
    return [get_deadline_status(a).model_dump() for a in assignments]


@router.post("/projects/{project_id}/run-sla-reminders")
async def trigger_sla_reminders(
    project_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """Manually trigger SLA reminder notifications for overdue/due-soon reviewers.

    Requires project manager access. Returns count of notifications sent.
    """
    project = _get_project_or_404(project_id)
    _require_manage_access(project, current_user)
    count = run_sla_reminders(project_id, project_name=project.name)
    return {"sent": count, "project_id": project_id}

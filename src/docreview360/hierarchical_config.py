# SPDX-License-Identifier: MIT
"""Hierarchical configuration: system defaults → org overrides → project overrides."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from .models import OrgConfig, ProjectConfig

# ---------------------------------------------------------------------------
# System defaults
# ---------------------------------------------------------------------------

SYSTEM_DEFAULTS: dict[str, Any] = {
    "auth.mfa_required": False,
    "auth.session_timeout_minutes": 480,
    "auth.max_concurrent_sessions": 5,
    "auth.password_min_length": 12,
    "documents.max_size_mb": 50,
    "documents.allowed_formats": ["docx", "pdf", "txt", "md", "html"],
    "documents.require_checklist": False,
    "reviews.require_two_reviewer_minimum": False,
    "reviews.allow_reviewer_reassignment": True,
    "workflows.allow_self_approval": True,
    "workflows.require_comment_on_rejection": True,
    "notifications.email_enabled": True,
    "notifications.slack_enabled": False,
    "ui.items_per_page": 25,
    "ui.default_theme": "system",
    "search.max_results": 200,
}


def get_config(
    db: Session,
    key: str,
    org_id: str | None = None,
    project_id: str | None = None,
) -> Any:
    """Resolve a config key using the hierarchy: project → org → system defaults.

    Raises KeyError if the key is not found anywhere.
    """
    # Project-level override (highest priority)
    if project_id is not None:
        row = (
            db.query(ProjectConfig)
            .filter(ProjectConfig.project_id == project_id, ProjectConfig.config_key == key)
            .first()
        )
        if row is not None:
            return json.loads(row.config_value)

    # Org-level override
    if org_id is not None:
        row = (
            db.query(OrgConfig)
            .filter(OrgConfig.org_id == org_id, OrgConfig.config_key == key)
            .first()
        )
        if row is not None:
            return json.loads(row.config_value)

    # System defaults (lowest priority)
    if key in SYSTEM_DEFAULTS:
        return SYSTEM_DEFAULTS[key]

    raise KeyError(f"Config key {key!r} not found")


def set_org_config(
    db: Session, org_id: str, key: str, value: Any, updated_by: str
) -> OrgConfig:
    """Set or update an org-level config override."""
    now = datetime.now(timezone.utc)
    row = (
        db.query(OrgConfig)
        .filter(OrgConfig.org_id == org_id, OrgConfig.config_key == key)
        .first()
    )
    if row is None:
        row = OrgConfig(id=str(uuid.uuid4()), org_id=org_id, config_key=key)
        db.add(row)
    row.config_value = json.dumps(value)
    row.updated_by = updated_by
    row.updated_at = now
    db.commit()
    db.refresh(row)
    return row


def set_project_config(
    db: Session, project_id: str, key: str, value: Any, updated_by: str
) -> ProjectConfig:
    """Set or update a project-level config override."""
    now = datetime.now(timezone.utc)
    row = (
        db.query(ProjectConfig)
        .filter(ProjectConfig.project_id == project_id, ProjectConfig.config_key == key)
        .first()
    )
    if row is None:
        row = ProjectConfig(id=str(uuid.uuid4()), project_id=project_id, config_key=key)
        db.add(row)
    row.config_value = json.dumps(value)
    row.updated_by = updated_by
    row.updated_at = now
    db.commit()
    db.refresh(row)
    return row


def get_org_config_all(db: Session, org_id: str) -> dict[str, Any]:
    """Return merged config: system defaults overridden by org settings."""
    result = dict(SYSTEM_DEFAULTS)
    rows = db.query(OrgConfig).filter(OrgConfig.org_id == org_id).all()
    for row in rows:
        result[row.config_key] = json.loads(row.config_value)
    return result


def get_project_config_all(
    db: Session, project_id: str, org_id: str | None = None
) -> dict[str, Any]:
    """Return merged config: system → org → project overrides."""
    result = dict(SYSTEM_DEFAULTS)
    if org_id is not None:
        org_rows = db.query(OrgConfig).filter(OrgConfig.org_id == org_id).all()
        for row in org_rows:
            result[row.config_key] = json.loads(row.config_value)
    proj_rows = (
        db.query(ProjectConfig).filter(ProjectConfig.project_id == project_id).all()
    )
    for row in proj_rows:
        result[row.config_key] = json.loads(row.config_value)
    return result


def delete_org_config(db: Session, org_id: str, key: str) -> bool:
    """Delete an org-level config override. Returns True if deleted."""
    row = (
        db.query(OrgConfig)
        .filter(OrgConfig.org_id == org_id, OrgConfig.config_key == key)
        .first()
    )
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True


def delete_project_config(db: Session, project_id: str, key: str) -> bool:
    """Delete a project-level config override. Returns True if deleted."""
    row = (
        db.query(ProjectConfig)
        .filter(ProjectConfig.project_id == project_id, ProjectConfig.config_key == key)
        .first()
    )
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True

"""Multi-tenant organization management for DocReview360.

Provides CRUD operations and per-organization configuration backed by
SQLAlchemy (Organization model in models.py).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field

from .db_store import get_db

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic settings model
# ---------------------------------------------------------------------------


class OrganizationSettings(BaseModel):
    """Per-organization configuration settings."""

    max_users: int = Field(default=0, ge=0, description="0 = unlimited")
    allowed_doc_types: list[str] = Field(default_factory=list)
    branding: dict[str, Any] = Field(default_factory=dict)
    custom_phases: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _org_to_dict(row: Any) -> dict[str, Any]:
    """Convert an ORM row or SQLAlchemy mapping to a plain dict."""
    settings_raw = getattr(row, "settings_json", None) or "{}"
    if isinstance(settings_raw, str):
        try:
            settings = json.loads(settings_raw)
        except (ValueError, TypeError):
            settings = {}
    elif isinstance(settings_raw, dict):
        settings = settings_raw
    else:
        settings = {}
    return {
        "id": row.id,
        "name": row.name,
        "settings": settings,
    }


def _parse_settings(settings: OrganizationSettings | dict[str, Any] | None) -> str:
    """Serialize settings to a JSON string for storage."""
    if settings is None:
        return "{}"
    if isinstance(settings, OrganizationSettings):
        return settings.model_dump_json()
    return json.dumps(settings)


# ---------------------------------------------------------------------------
# CRUD operations
# ---------------------------------------------------------------------------


def list_organizations(db: Any | None = None) -> list[dict[str, Any]]:
    """Return all organizations as a list of dicts.

    Args:
        db: Optional Database instance; uses the shared instance if omitted.

    Returns:
        List of organization dicts with id, name, and settings.
    """
    if db is None:
        db = get_db()
    from sqlalchemy import text as _text

    with db.session() as conn:
        rows = conn.execute(_text("SELECT id, name, settings_json FROM organizations")).fetchall()
    return [
        {
            "id": r[0],
            "name": r[1],
            "settings": _safe_json(r[2]),
        }
        for r in rows
    ]


def _safe_json(raw: Any) -> dict[str, Any]:
    """Safely parse a JSON string into a dict."""
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return {}


def get_organization(db: Any | None = None, org_id: int = 0) -> dict[str, Any]:
    """Return a single organization by ID.

    Args:
        db: Optional Database instance.
        org_id: Primary key of the organization.

    Returns:
        Organization dict.

    Raises:
        KeyError: If no organization with ``org_id`` exists.
    """
    if db is None:
        db = get_db()
    from sqlalchemy import text as _text

    with db.session() as conn:
        row = conn.execute(
            _text("SELECT id, name, settings_json FROM organizations WHERE id = :id"),
            {"id": org_id},
        ).fetchone()
    if row is None:
        raise KeyError(f"Organization {org_id} not found")
    return {"id": row[0], "name": row[1], "settings": _safe_json(row[2])}


def create_organization(
    db: Any | None = None,
    name: str = "",
    settings: OrganizationSettings | dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a new organization.

    Args:
        db: Optional Database instance.
        name: Unique organization name.
        settings: Optional per-org settings.

    Returns:
        Newly created organization dict.

    Raises:
        ValueError: If ``name`` is empty or already exists.
    """
    name = name.strip()
    if not name:
        raise ValueError("Organization name must not be empty")
    if db is None:
        db = get_db()
    from sqlalchemy import text as _text

    settings_json = _parse_settings(settings)
    try:
        with db.session() as conn:
            conn.execute(
                _text(
                    "INSERT INTO organizations (name, settings_json) VALUES (:name, :settings_json)"
                ),
                {"name": name, "settings_json": settings_json},
            )
            row = conn.execute(
                _text("SELECT id, name, settings_json FROM organizations WHERE name = :name"),
                {"name": name},
            ).fetchone()
    except Exception as exc:
        _logger.error("Failed to create organization '%s': %s", name, exc)
        raise ValueError(f"Could not create organization: {exc}") from exc
    if row is None:  # pragma: no cover — defensive
        raise ValueError("Organization creation failed unexpectedly")
    return {"id": row[0], "name": row[1], "settings": _safe_json(row[2])}


def update_organization(
    db: Any | None = None,
    org_id: int = 0,
    name: str | None = None,
    settings: OrganizationSettings | dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Update name and/or settings of an existing organization.

    Args:
        db: Optional Database instance.
        org_id: Primary key of the organization to update.
        name: New name (skipped if None).
        settings: New settings (skipped if None).

    Returns:
        Updated organization dict.

    Raises:
        KeyError: If the organization does not exist.
        ValueError: If ``name`` is the empty string after stripping.
    """
    if db is None:
        db = get_db()
    from sqlalchemy import text as _text

    # Verify existence first.
    existing = get_organization(db, org_id)  # raises KeyError if missing

    updates: dict[str, Any] = {}
    if name is not None:
        name = name.strip()
        if not name:
            raise ValueError("Organization name must not be empty")
        updates["name"] = name
    if settings is not None:
        updates["settings_json"] = _parse_settings(settings)

    if updates:
        set_clause = ", ".join(f"{k} = :{k}" for k in updates)
        updates["id"] = org_id
        with db.session() as conn:
            conn.execute(
                _text(f"UPDATE organizations SET {set_clause} WHERE id = :id"),
                updates,
            )

    return get_organization(db, org_id)


def delete_organization(db: Any | None = None, org_id: int = 0) -> None:
    """Delete an organization.

    Args:
        db: Optional Database instance.
        org_id: Primary key of the organization.

    Raises:
        KeyError: If the organization does not exist.
    """
    if db is None:
        db = get_db()
    from sqlalchemy import text as _text

    # Verify existence first.
    get_organization(db, org_id)  # raises KeyError if missing

    with db.session() as conn:
        # Disassociate any users assigned to this org.
        conn.execute(
            _text("UPDATE users SET organization_id = NULL WHERE organization_id = :id"),
            {"id": org_id},
        )
        conn.execute(
            _text("DELETE FROM organizations WHERE id = :id"),
            {"id": org_id},
        )
    _logger.info("Organization %d deleted", org_id)


# ---------------------------------------------------------------------------
# Settings helpers
# ---------------------------------------------------------------------------


def get_org_settings(db: Any | None = None, org_id: int = 0) -> OrganizationSettings:
    """Return the per-organization settings.

    Args:
        db: Optional Database instance.
        org_id: Primary key of the organization.

    Returns:
        :class:`OrganizationSettings` for the organization.

    Raises:
        KeyError: If the organization does not exist.
    """
    org = get_organization(db, org_id)
    raw = org.get("settings") or {}
    try:
        return OrganizationSettings(**raw)
    except Exception as exc:
        _logger.warning("Could not parse settings for org %d: %s — using defaults", org_id, exc)
        return OrganizationSettings()


def update_org_settings(
    db: Any | None = None,
    org_id: int = 0,
    settings: OrganizationSettings | None = None,
) -> OrganizationSettings:
    """Persist new per-organization settings.

    Args:
        db: Optional Database instance.
        org_id: Primary key of the organization.
        settings: New :class:`OrganizationSettings` to store.

    Returns:
        The updated :class:`OrganizationSettings`.

    Raises:
        KeyError: If the organization does not exist.
    """
    if settings is None:
        settings = OrganizationSettings()
    update_organization(db, org_id, settings=settings)
    return get_org_settings(db, org_id)


# ---------------------------------------------------------------------------
# User-assignment helpers
# ---------------------------------------------------------------------------


def assign_user_to_org(
    db: Any | None = None, username: str = "", org_id: int = 0
) -> None:
    """Assign a user to an organization.

    Args:
        db: Optional Database instance.
        username: Username of the user to assign.
        org_id: Primary key of the target organization.

    Raises:
        KeyError: If the organization or user does not exist.
    """
    username = username.strip()
    if not username:
        raise ValueError("username must not be empty")
    if db is None:
        db = get_db()
    from sqlalchemy import text as _text

    # Verify organization exists.
    get_organization(db, org_id)

    with db.session() as conn:
        row = conn.execute(
            _text("SELECT id FROM users WHERE username = :username"),
            {"username": username},
        ).fetchone()
        if row is None:
            raise KeyError(f"User '{username}' not found")
        conn.execute(
            _text("UPDATE users SET organization_id = :org_id WHERE username = :username"),
            {"org_id": org_id, "username": username},
        )
    _logger.info("User '%s' assigned to organization %d", username, org_id)


def remove_user_from_org(db: Any | None = None, username: str = "") -> None:
    """Remove a user from their current organization.

    Args:
        db: Optional Database instance.
        username: Username of the user to disassociate.

    Raises:
        KeyError: If the user does not exist.
    """
    username = username.strip()
    if not username:
        raise ValueError("username must not be empty")
    if db is None:
        db = get_db()
    from sqlalchemy import text as _text

    with db.session() as conn:
        row = conn.execute(
            _text("SELECT id FROM users WHERE username = :username"),
            {"username": username},
        ).fetchone()
        if row is None:
            raise KeyError(f"User '{username}' not found")
        conn.execute(
            _text("UPDATE users SET organization_id = NULL WHERE username = :username"),
            {"username": username},
        )
    _logger.info("User '%s' removed from organization", username)


def get_user_org(db: Any | None = None, username: str = "") -> dict[str, Any] | None:
    """Return the organization of a user, or ``None`` if unassigned.

    Args:
        db: Optional Database instance.
        username: Username to look up.

    Returns:
        Organization dict or ``None``.
    """
    username = username.strip()
    if not username:
        return None
    if db is None:
        db = get_db()
    from sqlalchemy import text as _text

    with db.session() as conn:
        row = conn.execute(
            _text(
                "SELECT o.id, o.name, o.settings_json "
                "FROM users u "
                "JOIN organizations o ON u.organization_id = o.id "
                "WHERE u.username = :username"
            ),
            {"username": username},
        ).fetchone()
    if row is None:
        return None
    return {"id": row[0], "name": row[1], "settings": _safe_json(row[2])}


def list_org_users(db: Any | None = None, org_id: int = 0) -> list[dict[str, Any]]:
    """Return all users belonging to an organization.

    Args:
        db: Optional Database instance.
        org_id: Primary key of the organization.

    Returns:
        List of user dicts with ``username`` and ``active`` fields.

    Raises:
        KeyError: If the organization does not exist.
    """
    if db is None:
        db = get_db()
    from sqlalchemy import text as _text

    # Verify existence.
    get_organization(db, org_id)

    with db.session() as conn:
        rows = conn.execute(
            _text(
                "SELECT username, active FROM users WHERE organization_id = :org_id"
            ),
            {"org_id": org_id},
        ).fetchall()
    return [{"username": r[0], "active": bool(r[1])} for r in rows]

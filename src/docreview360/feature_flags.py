# SPDX-License-Identifier: MIT
"""Per-organization feature flag management."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from .models import FeatureFlag

# ---------------------------------------------------------------------------
# Built-in flag defaults (enabled/disabled when no DB override exists)
# ---------------------------------------------------------------------------

BUILT_IN_FLAGS: dict[str, bool] = {
    "document_branches": True,
    "ai_rewrite": True,
    "regulatory_checker": True,
    "advanced_search": True,
    "webauthn": True,
    "oidc_login": True,
    "saml_login": True,
    "ldap_login": True,
    "legal_hold": True,
    "nara_metadata": True,
    "custom_workflows": True,
    "custom_fields": True,
    "hierarchical_config": True,
    "ediscovery": False,
    "beta_editor": False,
    "plugin_sandboxing": False,
}


def is_flag_enabled(
    db: Session,
    flag_name: str,
    org_id: str | None = None,
    user_id: str | None = None,
) -> bool:
    """Return True if a feature flag is enabled for the given org/user.

    Resolution order:
    1. Org-specific flag (if org_id provided)
    2. System-wide flag (org_id IS NULL)
    3. BUILT_IN_FLAGS default

    Rollout percentage < 100 uses a deterministic hash of flag_name + user_id.
    """
    # Org-specific override
    if org_id is not None:
        row = (
            db.query(FeatureFlag)
            .filter(FeatureFlag.flag_name == flag_name, FeatureFlag.org_id == org_id)
            .first()
        )
        if row is not None:
            return _apply_rollout(row, flag_name, user_id)

    # System-wide flag
    row = (
        db.query(FeatureFlag)
        .filter(FeatureFlag.flag_name == flag_name, FeatureFlag.org_id.is_(None))
        .first()
    )
    if row is not None:
        return _apply_rollout(row, flag_name, user_id)

    # Built-in default
    return BUILT_IN_FLAGS.get(flag_name, False)


def _apply_rollout(row: FeatureFlag, flag_name: str, user_id: str | None) -> bool:
    """Apply rollout_percentage check if < 100."""
    if not row.enabled:
        return False
    if row.rollout_percentage >= 100:
        return True
    if row.rollout_percentage <= 0:
        return False
    # Deterministic hash-based rollout
    key = f"{flag_name}:{user_id or ''}"
    bucket = int(hashlib.md5(key.encode(), usedforsecurity=False).hexdigest(), 16) % 100  # noqa: S324
    return bucket < row.rollout_percentage


def set_flag(
    db: Session,
    flag_name: str,
    enabled: bool,
    org_id: str | None = None,
    rollout_percentage: int = 100,
    created_by: str = "system",
) -> FeatureFlag:
    """Create or update a feature flag."""
    now = datetime.now(timezone.utc)
    q = db.query(FeatureFlag).filter(FeatureFlag.flag_name == flag_name)
    if org_id is not None:
        q = q.filter(FeatureFlag.org_id == org_id)
    else:
        q = q.filter(FeatureFlag.org_id.is_(None))
    row = q.first()
    if row is None:
        row = FeatureFlag(
            id=str(uuid.uuid4()),
            flag_name=flag_name,
            org_id=org_id,
            created_by=created_by,
            created_at=now,
        )
        db.add(row)
    row.enabled = enabled
    row.rollout_percentage = max(0, min(100, rollout_percentage))
    row.updated_at = now
    db.commit()
    db.refresh(row)
    return row


def list_flags(
    db: Session, org_id: str | None = None, user_id: str | None = None
) -> list[dict[str, Any]]:
    """Return all known flags with their effective enabled state."""
    db_flags = db.query(FeatureFlag).all()
    known_names = set(BUILT_IN_FLAGS.keys()) | {f.flag_name for f in db_flags}

    result = []
    for name in sorted(known_names):
        effective = is_flag_enabled(db, name, org_id=org_id, user_id=user_id)
        result.append(
            {
                "flag_name": name,
                "enabled": effective,
                "built_in_default": BUILT_IN_FLAGS.get(name),
            }
        )
    return result


def delete_flag(db: Session, flag_name: str, org_id: str | None = None) -> bool:
    """Remove a custom flag override, reverting to built-in default."""
    q = db.query(FeatureFlag).filter(FeatureFlag.flag_name == flag_name)
    if org_id is not None:
        q = q.filter(FeatureFlag.org_id == org_id)
    else:
        q = q.filter(FeatureFlag.org_id.is_(None))
    row = q.first()
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True

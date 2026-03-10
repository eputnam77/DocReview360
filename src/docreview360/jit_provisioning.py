# SPDX-License-Identifier: MIT
"""Just-in-time user provisioning from IdP identity claims."""

from __future__ import annotations

import json
import os
import secrets
from typing import Any

_TRUE_VALUES = {"1", "true", "yes", "on"}


def jit_enabled() -> bool:
    """Return True if JIT provisioning is enabled via env flag."""
    return os.environ.get("DOCREVIEW360_JIT_ENABLED", "true").strip().lower() in _TRUE_VALUES


def _load_role_map() -> dict[str, str]:
    """Parse DOCREVIEW360_JIT_ROLE_MAP JSON; return empty dict on error."""
    raw = os.environ.get("DOCREVIEW360_JIT_ROLE_MAP", "{}").strip()
    try:
        result = json.loads(raw)
        return result if isinstance(result, dict) else {}
    except Exception:
        return {}


def _extract_username(claims: dict[str, Any]) -> str | None:
    """Extract username from claims using configured claim key with fallbacks."""
    key = os.environ.get("DOCREVIEW360_JIT_USERNAME_CLAIM", "preferred_username").strip()
    for candidate in (key, "email", "sub"):
        value = claims.get(candidate)
        if value and isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_roles(claims: dict[str, Any]) -> list[str]:
    """Extract and map roles from claims, applying role map and default roles."""
    role_claim = os.environ.get("DOCREVIEW360_JIT_ROLES_CLAIM", "roles").strip()
    raw_roles: list[str] = []

    for candidate in (role_claim, "groups"):
        value = claims.get(candidate)
        if isinstance(value, list):
            raw_roles = [str(r) for r in value if r]
            break
        if isinstance(value, str) and value:
            raw_roles = [value]
            break

    role_map = _load_role_map()
    mapped: list[str] = []
    for role in raw_roles:
        mapped.append(role_map.get(role, role))

    # Add default roles
    defaults_raw = os.environ.get("DOCREVIEW360_JIT_DEFAULT_ROLES", "").strip()
    if defaults_raw:
        for r in defaults_raw.split(","):
            r = r.strip()
            if r and r not in mapped:
                mapped.append(r)

    # Deduplicate while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for r in mapped:
        if r not in seen:
            seen.add(r)
            result.append(r)
    return result


def _sync_roles(username: str, roles: list[str]) -> None:
    """Assign DocReview360 roles to ``username``."""
    try:
        from .rbac import add_role
    except Exception:
        return
    for role in roles:
        try:
            add_role(username, role)
        except Exception:
            pass


def provision_user_from_claims(
    claims: dict[str, Any],
    auth_method: str,
    *,
    force_reprovision: bool = False,
) -> tuple[str, list[str]]:
    """Provision or sync a user from IdP claims.

    Returns ``(username, roles)``.  Raises ``ValueError`` when no username
    can be determined from the supplied claims.
    """
    username = _extract_username(claims)
    if not username:
        raise ValueError("Cannot provision user: no username claim found")

    roles = _extract_roles(claims)

    try:
        from .auth import _get_user_repository
        repo = _get_user_repository()
        existing = repo.get_user(username)
        if existing is None or force_reprovision:
            repo._seed_user(username, secrets.token_hex(32), active=True)
    except Exception:
        pass

    _sync_roles(username, roles)

    try:
        from .logs import log_event
        log_event(
            "jit_provision",
            user_id=username,
            auth_method=auth_method,
            roles=roles,
        )
    except Exception:
        pass

    return username, roles


def extract_username_from_claims(claims: dict[str, Any]) -> str | None:
    """Public alias for :func:`_extract_username`."""
    return _extract_username(claims)

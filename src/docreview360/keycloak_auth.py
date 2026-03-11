# SPDX-License-Identifier: MIT
"""Keycloak-specific OIDC integration.

Handles Keycloak realm/client role claim extraction and mapping
to DocReview360 roles.

Keycloak-specific environment variables
----------------------------------------
KEYCLOAK_REALM_ROLES_CLAIM
    Top-level claim key that contains realm-level role data.
    Keycloak puts an object like ``{"roles": ["offline_access", ...]}`` here.
    Default: ``"realm_access"``.

KEYCLOAK_CLIENT_ID_FOR_ROLES
    The Keycloak client_id whose ``resource_access`` roles should be mapped.
    Defaults to the value of ``OIDC_CLIENT_ID`` when unset.

KEYCLOAK_ROLE_MAP
    JSON object mapping raw Keycloak role names to DocReview360 role names.
    Example: ``{"docreview-admin": "admin", "docreview-reviewer": "reviewer"}``.
    Default: ``{}``.

KEYCLOAK_DEFAULT_ROLE
    Role assigned to the user when none of their Keycloak roles appear in
    ``KEYCLOAK_ROLE_MAP``.  Default: ``"reviewer"``.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration helpers (read env at call-time so tests can monkeypatch)
# ---------------------------------------------------------------------------


def _realm_roles_claim() -> str:
    return os.environ.get("KEYCLOAK_REALM_ROLES_CLAIM", "realm_access").strip()


def _client_id_for_roles() -> str:
    """Return the client_id whose resource_access roles to extract."""
    val = os.environ.get("KEYCLOAK_CLIENT_ID_FOR_ROLES", "").strip()
    if val:
        return val
    # Fall back to the generic OIDC client_id
    return os.environ.get("OIDC_CLIENT_ID", "").strip()


def _load_role_map() -> dict[str, str]:
    """Parse KEYCLOAK_ROLE_MAP JSON; return empty dict on any error."""
    raw = os.environ.get("KEYCLOAK_ROLE_MAP", "{}").strip()
    try:
        result = json.loads(raw)
        return result if isinstance(result, dict) else {}
    except Exception:
        return {}


def _default_role() -> str:
    return os.environ.get("KEYCLOAK_DEFAULT_ROLE", "reviewer").strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_keycloak_roles(claims: dict[str, Any]) -> list[str]:
    """Extract raw Keycloak role strings from ``claims``.

    Combines roles from:

    * ``realm_access.roles`` (controlled by ``KEYCLOAK_REALM_ROLES_CLAIM``)
    * ``resource_access.<client_id>.roles`` (controlled by
      ``KEYCLOAK_CLIENT_ID_FOR_ROLES`` / ``OIDC_CLIENT_ID``)

    Duplicate role names are removed while preserving first-seen order.
    """
    roles: list[str] = []
    seen: set[str] = set()

    def _add(role: str) -> None:
        if role and role not in seen:
            seen.add(role)
            roles.append(role)

    # --- realm_access.roles ---
    realm_claim = _realm_roles_claim()
    realm_obj = claims.get(realm_claim)
    if isinstance(realm_obj, dict):
        for r in realm_obj.get("roles", []):
            if isinstance(r, str):
                _add(r)

    # --- resource_access.<client_id>.roles ---
    client_id = _client_id_for_roles()
    if client_id:
        resource_access = claims.get("resource_access")
        if isinstance(resource_access, dict):
            client_obj = resource_access.get(client_id)
            if isinstance(client_obj, dict):
                for r in client_obj.get("roles", []):
                    if isinstance(r, str):
                        _add(r)

    return roles


def map_keycloak_roles_to_docreview(keycloak_roles: list[str]) -> list[str]:
    """Map a list of raw Keycloak role strings to DocReview360 roles.

    Applies ``KEYCLOAK_ROLE_MAP`` to each entry.  If the role appears in
    the map, the mapped value is used; otherwise the raw role string is
    discarded (unmapped Keycloak roles are *not* passed through verbatim).

    When the resulting list is empty — meaning no Keycloak role matched the
    map — returns ``[KEYCLOAK_DEFAULT_ROLE]`` so the user always receives at
    least one role.
    """
    role_map = _load_role_map()
    mapped: list[str] = []
    seen: set[str] = set()

    for role in keycloak_roles:
        docreview_role = role_map.get(role)
        if docreview_role and docreview_role not in seen:
            seen.add(docreview_role)
            mapped.append(docreview_role)

    if not mapped:
        default = _default_role()
        if default:
            mapped.append(default)

    return mapped


def get_user_info_from_keycloak_claims(claims: dict[str, Any]) -> dict[str, Any]:
    """Extract user-profile information from Keycloak ID-token claims.

    Returns a dict with keys:

    * ``username`` — from ``preferred_username``, ``email``, or ``sub``
    * ``email`` — from ``email`` (empty string if absent)
    * ``full_name`` — from ``name``, or ``given_name + family_name``
    * ``roles`` — DocReview360 roles mapped from Keycloak claims
    """
    username: str = (
        claims.get("preferred_username")
        or claims.get("email")
        or claims.get("sub")
        or ""
    )

    email: str = claims.get("email") or ""

    full_name: str = claims.get("name") or ""
    if not full_name:
        given = claims.get("given_name") or ""
        family = claims.get("family_name") or ""
        full_name = f"{given} {family}".strip()

    raw_roles = extract_keycloak_roles(claims)
    roles = map_keycloak_roles_to_docreview(raw_roles)

    return {
        "username": username,
        "email": email,
        "full_name": full_name,
        "roles": roles,
    }


def is_keycloak_provider(provider_url: str) -> bool:
    """Return True when ``provider_url`` looks like a Keycloak instance.

    Matches URLs that contain the literal string ``"keycloak"`` (case-insensitive)
    or the ``"/realms/"`` path segment that Keycloak uses for its realm URLs.
    """
    lower = provider_url.lower()
    return "keycloak" in lower or "/realms/" in lower

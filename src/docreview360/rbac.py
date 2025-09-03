"""Role-based access control helpers.

Simple role based access helpers.

The tests in this kata reload the :mod:`docreview360.rbac` module multiple
times using :func:`importlib`. A straight re-import would create a brand new
``USER_ROLES`` mapping for every load which means that different module
instances no longer share the same in-memory role assignments. FastAPI
dependencies captured during the first import would keep referencing the
original mapping and therefore miss any roles added later, leading to
``403 Forbidden`` responses even though a role had been granted in the latest
module instance.

To make the role store resilient across reloads we stash the state in a small
private module (``docreview360._rbac_state``). Subsequent imports simply reuse
the same dictionary so all parts of the application observe consistent role
changes regardless of how many times the module is re-imported.
"""

from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import Callable, Iterable, Set

from fastapi import Depends, HTTPException, status

from . import auth

# A shared state container that survives module reloads.  ``importlib`` based
# tests load :mod:`docreview360.rbac` multiple times which would normally create
# independent ``USER_ROLES`` dictionaries.  Storing the mapping on a dedicated
# module keeps the state consistent across imports.
_state = sys.modules.setdefault("docreview360._rbac_state", SimpleNamespace())

# Default permission table for roles. Each role maps to the set of actions it
# may perform.  ``ROLE_PERMISSIONS`` is effectively constant but placing it on
# the shared state keeps behaviour predictable when reloading.
if not hasattr(_state, "ROLE_PERMISSIONS"):
    _state.ROLE_PERMISSIONS = {
        "admin": {
            "create",
            "read",
            "update",
            "delete",
            "edit_field_x",
            "view_audit_log",
            "verification_override",
        },
        "manager": {"create", "read", "update"},
        "sme": {"read", "edit_field_x"},
        "reviewer": {"read"},
        "editor": {"read", "update"},
        "observer": {"read"},
        "user": {"read"},
        "auditor": {"view_audit_log"},
        "verifier": {"verification_override"},
    }
ROLE_PERMISSIONS: dict[str, Set[str]] = _state.ROLE_PERMISSIONS

# In-memory mapping of usernames to role sets.  Stored on ``_state`` so that all
# imports share the same dictionary.
if not hasattr(_state, "USER_ROLES"):
    _state.USER_ROLES = {
        "alice": {"user", "admin"},
        "bob": {"auditor"},
        "system": {"admin"},
    }
USER_ROLES: dict[str, Set[str]] = _state.USER_ROLES


def set_user_roles(username: str, roles: Iterable[str]) -> None:
    """Assign ``roles`` to ``username`` replacing any existing mapping.

    Role names are normalized to lower-case so that lookups become
    case-insensitive.  This mirrors how roles are typically stored in
    backing stores and avoids subtle bugs where callers pass ``"Admin"``
    instead of ``"admin"``.
    """

    USER_ROLES[username] = {r.lower() for r in roles}


def add_role(username: str, role: str) -> None:
    """Add a single ``role`` to ``username``.

    The provided ``role`` is stored in lower-case to keep the mapping
    normalized.  Re-adding an existing role is a no-op.
    """

    USER_ROLES.setdefault(username, set()).add(role.lower())


def get_roles(username: str) -> set[str]:
    """Return all roles assigned to ``username``."""
    return USER_ROLES.get(username, set())


def has_role(username: str, role: str) -> bool:
    """Return ``True`` if ``username`` is assigned ``role``.

    The check is case-insensitive to match the behaviour of
    :func:`add_role` and :func:`set_user_roles`.
    """

    return role.lower() in USER_ROLES.get(username, set())


def has_permission(username: str, action: str) -> bool:
    """Return ``True`` if ``username`` may perform ``action`` based on roles."""
    roles = {r.lower() for r in get_roles(username)}
    act = action.lower()
    return any(act in ROLE_PERMISSIONS.get(r, set()) for r in roles)


def require_role(role: str) -> Callable[[auth.User], auth.User]:
    """Return a dependency ensuring the current user has ``role``."""

    def _dependency(user: auth.User = Depends(auth.get_current_user)) -> auth.User:
        if not has_role(user.username, role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return user

    return _dependency


def require_permission(action: str) -> Callable[[auth.User], auth.User]:
    """Return a dependency ensuring the user has permission ``action``."""

    def _dependency(user: auth.User = Depends(auth.get_current_user)) -> auth.User:
        if not has_permission(user.username, action):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return user

    return _dependency

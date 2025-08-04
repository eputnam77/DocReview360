"""Role-based access control helpers."""

from __future__ import annotations

from typing import Callable, Iterable, Set

from fastapi import Depends, HTTPException, status

from . import auth

# Default permission table for seven roles. Each role maps to the set of
# actions it may perform. The table acts as a source of truth for tests and
# runtime checks.
ROLE_PERMISSIONS: dict[str, Set[str]] = {
    "admin": {"create", "read", "update", "delete", "edit_field_x"},
    "manager": {"create", "read", "update"},
    "sme": {"read", "edit_field_x"},
    "reviewer": {"read"},
    "editor": {"read", "update"},
    "observer": {"read"},
    "user": {"read"},
}

# In-memory mapping of usernames to role sets
USER_ROLES: dict[str, Set[str]] = {"alice": {"user"}}


def set_user_roles(username: str, roles: Iterable[str]) -> None:
    """Assign ``roles`` to ``username`` replacing any existing mapping."""
    USER_ROLES[username] = set(roles)


def add_role(username: str, role: str) -> None:
    """Add a single ``role`` to ``username``."""
    USER_ROLES.setdefault(username, set()).add(role)


def get_roles(username: str) -> set[str]:
    """Return all roles assigned to ``username``."""
    return USER_ROLES.get(username, set())


def has_role(username: str, role: str) -> bool:
    """Return ``True`` if ``username`` is assigned ``role``."""
    return role in USER_ROLES.get(username, set())


def has_permission(username: str, action: str) -> bool:
    """Return ``True`` if ``username`` may perform ``action`` based on roles."""
    roles = get_roles(username)
    return any(action in ROLE_PERMISSIONS.get(r, set()) for r in roles)


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

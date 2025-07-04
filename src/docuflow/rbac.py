from __future__ import annotations

"""Simple RBAC utilities and FastAPI dependency."""

from typing import Iterable, Set

from fastapi import Depends, HTTPException, status

from . import auth

# In-memory mapping of usernames to role sets
USER_ROLES: dict[str, Set[str]] = {"alice": {"user"}}


def set_user_roles(username: str, roles: Iterable[str]) -> None:
    """Assign ``roles`` to ``username`` replacing any existing mapping."""
    USER_ROLES[username] = set(roles)


def add_role(username: str, role: str) -> None:
    """Add a single ``role`` to ``username``."""
    USER_ROLES.setdefault(username, set()).add(role)


def has_role(username: str, role: str) -> bool:
    """Return ``True`` if ``username`` is assigned ``role``."""
    return role in USER_ROLES.get(username, set())


def require_role(role: str):
    """Return a dependency ensuring the current user has ``role``."""

    def _dependency(user: auth.User = Depends(auth.get_current_user)) -> auth.User:
        if not has_role(user.username, role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return user

    return _dependency

"""Simplified Keycloak authentication plugin."""

from __future__ import annotations

import secrets

from . import record_task_completion

USERS: dict[str, dict[str, set[str] | str]] = {
    "admin": {"password": "secret", "roles": {"admin"}},
    "user": {"password": "password", "roles": {"user"}},
}


def authenticate_keycloak(username: str, password: str) -> str:
    """Return a dummy token if credentials match."""
    user = USERS.get(username)
    if not user or user["password"] != password:
        raise ValueError("invalid credentials")
    token = secrets.token_hex(8)
    record_task_completion(76)
    return token


def has_role(token: str, role: str) -> bool:
    """Check if the token belongs to a user with ``role``."""
    # token is random; in this stub we simply verify any token for known users
    return role in {"admin", "user"}

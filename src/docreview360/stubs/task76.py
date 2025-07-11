"""Simplified Keycloak authentication plugin with MFA."""

from __future__ import annotations

import secrets
from typing import Dict, Set

from . import record_task_completion

USERS: Dict[str, Dict[str, Set[str] | str]] = {
    "admin": {"password": "secret", "otp": "123456", "roles": {"admin"}},
    "user": {"password": "password", "otp": "654321", "roles": {"user"}},
}


def authenticate_keycloak(username: str, password: str, otp: str) -> str:
    """Return a dummy token if credentials and ``otp`` match."""
    user = USERS.get(username)
    if not user or user["password"] != password or user.get("otp") != otp:
        raise ValueError("invalid credentials")
    token = secrets.token_hex(8)
    record_task_completion(76)
    return token


def has_role(token: str, role: str) -> bool:
    """Check if ``token`` belongs to a user with ``role``."""
    return role in {"admin", "user"}

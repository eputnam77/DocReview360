# SPDX-License-Identifier: MIT
"""Authentication package for DocReview360 — backward-compatible re-exports.

This package replaces the monolithic ``auth.py`` module.  All previously
public names remain importable from ``docreview360.auth``.
"""

from __future__ import annotations

import os
import secrets
import threading
import warnings
from datetime import timedelta
from functools import lru_cache
from pathlib import Path
from typing import Callable, TypeVar

T = TypeVar("T")

# ---------------------------------------------------------------------------
# Module-level constants (mirrors original auth.py top-level)
# ---------------------------------------------------------------------------

SAFE_DEFAULT_ENVS = {"", "dev", "development", "test", "testing"}
SAFE_SEED_ENVS = SAFE_DEFAULT_ENVS


def _current_environment() -> str:
    """Return the current deployment environment in lowercase."""
    return os.getenv("DOCREVIEW360_ENV", "").strip().lower()


def _allow_demo_seed() -> bool:
    """Return ``True`` when demo users may be seeded automatically."""
    return SEED_DEMO_USERS and _current_environment() in SAFE_SEED_ENVS


def _env_or_default(
    name: str,
    *,
    default: str,
    cast: Callable[[str], T] | None = None,
    required: bool = False,
    allow_defaults_in: set[str] = SAFE_DEFAULT_ENVS,
) -> T:
    """Return an environment variable or fall back to a development default."""
    value = os.getenv(name)
    if value is None or value == "":
        current_env = _current_environment()
        if required and current_env not in allow_defaults_in:
            raise RuntimeError(
                f"{name} environment variable must be set for the"
                f" {current_env or 'production'} environment."
            )
        warnings.warn(
            f"{name} environment variable not set; using development default",
            RuntimeWarning,
            stacklevel=2,
        )
        value = default

    return cast(value) if cast else value  # type: ignore[return-value]


DEFAULT_ALGORITHM = "HS256"
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
DEFAULT_TOKEN_ISSUER = "docreview360.local"
DEFAULT_TOKEN_AUDIENCE = "docreview360-users"
_GENERATED_DEV_SECRET_KEY = secrets.token_urlsafe(48)

SECRET_KEY = _env_or_default(
    "DOCREVIEW360_SECRET_KEY", default=_GENERATED_DEV_SECRET_KEY, required=True
)
SECRET_KEY_PREVIOUS: str | None = os.getenv("DOCREVIEW360_SECRET_KEY_PREVIOUS") or None
ALGORITHM = _env_or_default("DOCREVIEW360_ALGORITHM", default=DEFAULT_ALGORITHM)
ACCESS_TOKEN_EXPIRE_MINUTES = _env_or_default(
    "DOCREVIEW360_ACCESS_EXPIRE_MINUTES",
    default=str(DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES),
    cast=int,
)
TOKEN_ISSUER = _env_or_default("DOCREVIEW360_TOKEN_ISSUER", default=DEFAULT_TOKEN_ISSUER)
TOKEN_AUDIENCE = _env_or_default("DOCREVIEW360_TOKEN_AUDIENCE", default=DEFAULT_TOKEN_AUDIENCE)

DEFAULT_OIDC_SECRET_KEY = "docreview360-oidc-dev-secret"
DEFAULT_OIDC_TOKEN_EXPIRE_MINUTES = 30
DEFAULT_OIDC_TOKEN_ISSUER = "docreview360-oidc.local"
DEFAULT_OIDC_TOKEN_AUDIENCE = "docreview360-oidc"
_GENERATED_DEV_OIDC_SECRET_KEY = secrets.token_urlsafe(48)

OIDC_SECRET_KEY = _env_or_default(
    "DOCREVIEW360_OIDC_SECRET_KEY", default=_GENERATED_DEV_OIDC_SECRET_KEY, required=True
)
OIDC_SECRET_KEY_PREVIOUS: str | None = os.getenv("DOCREVIEW360_OIDC_SECRET_KEY_PREVIOUS") or None
OIDC_ALGORITHM = _env_or_default("DOCREVIEW360_OIDC_ALGORITHM", default=DEFAULT_ALGORITHM)
OIDC_TOKEN_EXPIRE_MINUTES = _env_or_default(
    "DOCREVIEW360_OIDC_EXPIRE_MINUTES",
    default=str(DEFAULT_OIDC_TOKEN_EXPIRE_MINUTES),
    cast=int,
)
OIDC_TOKEN_ISSUER = _env_or_default(
    "DOCREVIEW360_OIDC_TOKEN_ISSUER", default=DEFAULT_OIDC_TOKEN_ISSUER
)
OIDC_TOKEN_AUDIENCE = _env_or_default(
    "DOCREVIEW360_OIDC_TOKEN_AUDIENCE", default=DEFAULT_OIDC_TOKEN_AUDIENCE
)


def _as_bool(value: str) -> bool:
    """Return ``True`` when ``value`` represents an enabled boolean."""
    return value.strip().lower() in {"1", "true", "yes", "on"}


REQUIRE_MFA = _env_or_default("DOCREVIEW360_REQUIRE_MFA", default="false", cast=_as_bool)
SEED_DEMO_USERS = _env_or_default(
    "DOCREVIEW360_SEED_DEMO_USERS",
    default="true",
    cast=_as_bool,
)

_BANNED_NON_DEV_SECRETS = {
    "",
    "changeme",
    "change-me",
    "secret",
    "password",
    "docreview360-dev-secret",
    DEFAULT_OIDC_SECRET_KEY,
}


def _enforce_secret_strength() -> None:
    """Fail fast when insecure secrets are used outside local/test environments."""
    environment = _current_environment()
    if environment in SAFE_DEFAULT_ENVS:
        return
    if SECRET_KEY.strip().lower() in _BANNED_NON_DEV_SECRETS or len(SECRET_KEY.strip()) < 32:
        raise RuntimeError(
            "DOCREVIEW360_SECRET_KEY must be a unique high-entropy value (>=32 chars) "
            f"for the {environment or 'production'} environment."
        )
    if (
        OIDC_SECRET_KEY.strip().lower() in _BANNED_NON_DEV_SECRETS
        or len(OIDC_SECRET_KEY.strip()) < 32
    ):
        raise RuntimeError(
            "DOCREVIEW360_OIDC_SECRET_KEY must be a unique high-entropy value (>=32 chars) "
            f"for the {environment or 'production'} environment."
        )


_enforce_secret_strength()

MAX_FAILED_ATTEMPTS = _env_or_default(
    "DOCREVIEW360_MAX_FAILED_ATTEMPTS",
    default="5",
    cast=int,
)
LOCKOUT_SECONDS = _env_or_default(
    "DOCREVIEW360_LOCKOUT_SECONDS",
    default="300",
    cast=int,
)
LOCKOUT_DURATION = timedelta(seconds=LOCKOUT_SECONDS)


def _default_user_db_path() -> str:
    """Return the default path for the user credential store."""
    return str(Path("docreview360_users.db").resolve())


USER_DB_PATH = _env_or_default(
    "DOCREVIEW360_USER_DB",
    default=_default_user_db_path(),
)

DEMO_USER_DEFAULTS: dict[str, dict[str, str]] = {
    "alice": {
        "password": "password",
        "otp_secret": "123456",
    },
    "bob": {
        "password": "password",
        "otp_secret": "123456",
    },
}

# Keycloak stub
_KEYCLOAK_STUB_USERS: dict[str, dict[str, object]] = {
    "admin": {"password": "secret", "otp": "123456", "roles": {"admin"}},
    "user": {"password": "password", "otp": "654321", "roles": {"user"}},
}

# ---------------------------------------------------------------------------
# Sub-module imports — must come AFTER all module-level constants above
# ---------------------------------------------------------------------------

from ._models import (  # noqa: E402
    CHARACTER_CLASS_CHECKS,
    CHARACTER_CLASS_LABELS,
    PasswordPolicy,
    PasswordPolicyError,
    Token,
    User,
    UserRecord,
    _PBKDF2_ITERATIONS,
    _has_digits,
    _has_lowercase,
    _has_symbols,
    _has_uppercase,
    _hash_password_fallback,
    _verify_password_fallback,
)
from ._repository import UserRepository  # noqa: E402
from ._core import (  # noqa: E402
    _extract_otp,
    _get_user_repository,
    _require_csrf_token,
    authenticate_mfa,
    authenticate_user,
    configure_user_repository,
    create_access_token,
    create_id_token,
    get_current_user,
    get_current_user_oidc,
    is_active,
    is_token_revoked,
    login_for_access_token,
    login_for_oidc_token,
    oidc_scheme,
    oauth2_scheme,
    revoke_token,
)

# ---------------------------------------------------------------------------
# Repository singleton
# ---------------------------------------------------------------------------

USER_REPOSITORY = UserRepository(USER_DB_PATH)
_USER_REPOSITORY_LOCK = threading.Lock()


@lru_cache(maxsize=1)
def _password_policy() -> PasswordPolicy:
    """Return the cached password policy instance."""
    return PasswordPolicy.load()


# ---------------------------------------------------------------------------
# Keycloak helpers (stub)
# ---------------------------------------------------------------------------


def _authenticate_keycloak_stub(username: str, password: str, otp: str) -> str:
    """Return a dummy token if credentials and ``otp`` match against the stub user store."""
    user = _KEYCLOAK_STUB_USERS.get(username)
    if not user or user["password"] != password or user.get("otp") != otp:
        raise ValueError("invalid credentials")
    return secrets.token_hex(8)


authenticate_keycloak = _authenticate_keycloak_stub


def has_role(token: str, role: str) -> bool:
    """Check if ``token`` belongs to a user with ``role`` (stub implementation)."""
    return role in {"admin", "user"}


def keycloak_mfa_login(username: str, password: str, otp: str) -> str:
    """Return a token from the Keycloak MFA stub."""
    _env = _current_environment()
    _prod_envs = {"production", "prod", "staging"}
    _enabled = os.getenv("DOCREVIEW360_ENABLE_KEYCLOAK", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    if _env in _prod_envs and not _enabled:
        raise RuntimeError(
            "Keycloak MFA login is not available in production. "
            "The integration is not complete (stub only). "
            "Set DOCREVIEW360_ENABLE_KEYCLOAK=1 only after completing the real integration."
        )
    return _authenticate_keycloak_stub(username, password, otp)


__all__ = [
    # constants
    "SAFE_DEFAULT_ENVS",
    "SAFE_SEED_ENVS",
    "DEFAULT_ALGORITHM",
    "DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES",
    "DEFAULT_TOKEN_ISSUER",
    "DEFAULT_TOKEN_AUDIENCE",
    "SECRET_KEY",
    "SECRET_KEY_PREVIOUS",
    "ALGORITHM",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "TOKEN_ISSUER",
    "TOKEN_AUDIENCE",
    "DEFAULT_OIDC_SECRET_KEY",
    "DEFAULT_OIDC_TOKEN_EXPIRE_MINUTES",
    "DEFAULT_OIDC_TOKEN_ISSUER",
    "DEFAULT_OIDC_TOKEN_AUDIENCE",
    "OIDC_SECRET_KEY",
    "OIDC_SECRET_KEY_PREVIOUS",
    "OIDC_ALGORITHM",
    "OIDC_TOKEN_EXPIRE_MINUTES",
    "OIDC_TOKEN_ISSUER",
    "OIDC_TOKEN_AUDIENCE",
    "REQUIRE_MFA",
    "SEED_DEMO_USERS",
    "MAX_FAILED_ATTEMPTS",
    "LOCKOUT_SECONDS",
    "LOCKOUT_DURATION",
    "USER_DB_PATH",
    "DEMO_USER_DEFAULTS",
    "USER_REPOSITORY",
    # models
    "PasswordPolicyError",
    "PasswordPolicy",
    "Token",
    "User",
    "UserRecord",
    "CHARACTER_CLASS_CHECKS",
    "CHARACTER_CLASS_LABELS",
    # repository
    "UserRepository",
    # core functions
    "oauth2_scheme",
    "oidc_scheme",
    "revoke_token",
    "is_token_revoked",
    "is_active",
    "authenticate_user",
    "authenticate_mfa",
    "create_access_token",
    "create_id_token",
    "get_current_user",
    "get_current_user_oidc",
    "login_for_access_token",
    "login_for_oidc_token",
    "configure_user_repository",
    # keycloak stub
    "_authenticate_keycloak_stub",
    "authenticate_keycloak",
    "has_role",
    "keycloak_mfa_login",
    # private helpers re-exported
    "_current_environment",
    "_allow_demo_seed",
    "_env_or_default",
    "_as_bool",
    "_enforce_secret_strength",
    "_get_user_repository",
    "_password_policy",
    "_require_csrf_token",
    "_extract_otp",
    "_hash_password_fallback",
    "_verify_password_fallback",
    "_PBKDF2_ITERATIONS",
    "_KEYCLOAK_STUB_USERS",
    "_BANNED_NON_DEV_SECRETS",
    "_USER_REPOSITORY_LOCK",
]

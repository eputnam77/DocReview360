# SPDX-License-Identifier: MIT
"""Auth core — JWT creation/validation, token revocation, get_current_user, login handlers."""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt

from ._models import Token, User
from ._repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)
oidc_scheme = OAuth2PasswordBearer(tokenUrl="oidc/token", auto_error=False)


def _get_user_repository() -> UserRepository:
    """Return the active user repository, reloading if the DB path changed."""
    import sys
    from pathlib import Path

    # Get the auth package module (docreview360.auth)
    pkg_name = __name__.rpartition(".")[0]
    auth_mod = sys.modules.get(pkg_name)

    # Resolve which path we should be using
    user_db_env = os.getenv("DOCREVIEW360_USER_DB")
    if auth_mod is not None:
        default_path = getattr(auth_mod, "USER_DB_PATH", "docreview360_users.db")
    else:
        default_path = "docreview360_users.db"
    current_path = Path(user_db_env or default_path).resolve()

    if auth_mod is None:
        # Module not yet fully initialized — fall back to a temporary repo
        return UserRepository(str(current_path))

    repo = getattr(auth_mod, "USER_REPOSITORY", None)
    if repo is not None and repo._path.resolve() == current_path and current_path.exists():
        return repo

    lock = getattr(auth_mod, "_USER_REPOSITORY_LOCK", None)
    if lock is None:
        new_repo = UserRepository(str(current_path))
        setattr(auth_mod, "USER_REPOSITORY", new_repo)
        return new_repo

    with lock:
        repo = getattr(auth_mod, "USER_REPOSITORY", None)
        if repo is None or repo._path.resolve() != current_path or not current_path.exists():
            new_repo = UserRepository(str(current_path))
            setattr(auth_mod, "USER_REPOSITORY", new_repo)
            return new_repo
    return getattr(auth_mod, "USER_REPOSITORY")


def revoke_token(jti: str, expires_at: datetime) -> None:
    """Persist ``jti`` to the SQLite revocation table until it expires."""
    _get_user_repository().revoke_token(jti, expires_at)


def is_token_revoked(jti: str) -> bool:
    """Return ``True`` if ``jti`` has been revoked and has not yet expired."""
    return _get_user_repository().is_token_revoked(jti)


def is_active(username: str) -> bool:
    """Return ``True`` if ``username`` is marked active."""
    record = _get_user_repository().get_user(username)
    return bool(record and record.active)


def authenticate_user(username: str, password: str) -> User | None:
    """Return ``User`` if credentials match and user is active."""
    from . import DEMO_USER_DEFAULTS, _allow_demo_seed

    if not username or not password:
        return None

    repo = _get_user_repository()
    record = repo.get_user(username)
    if record is None:
        demo_defaults = DEMO_USER_DEFAULTS.get(username)
        if (
            demo_defaults
            and password == demo_defaults.get("password")
            and _allow_demo_seed()
        ):
            repo._seed_user(
                username,
                password,
                otp_secret=demo_defaults.get("otp_secret"),
                active=True,
            )
            record = repo.get_user(username)
    if not record or not record.active:
        return None
    if repo.is_locked(record):
        return None
    if not UserRepository.verify_password(password, record.password_hash):
        demo_defaults = DEMO_USER_DEFAULTS.get(username)
        if (
            demo_defaults
            and password == demo_defaults.get("password")
            and _allow_demo_seed()
        ):
            repo._seed_user(
                username,
                password,
                otp_secret=record.otp_secret,
                active=bool(record.active),
            )
            repo.reset_failures(username)
            return User(username=username, active=True)
        repo.record_failure(username)
        return None
    repo.reset_failures(username)
    return User(username=username, active=True)


def authenticate_mfa(username: str, password: str, otp: str) -> User | None:
    """Return ``User`` if credentials, OTP match, and user is active."""
    from . import DEMO_USER_DEFAULTS, SEED_DEMO_USERS

    if not username or not password or not otp:
        return None
    repo = _get_user_repository()
    record = repo.get_user(username)
    if not record or not record.active:
        return None
    if repo.is_locked(record):
        return None
    if not UserRepository.verify_password(password, record.password_hash):
        demo_defaults = DEMO_USER_DEFAULTS.get(username)
        if SEED_DEMO_USERS and demo_defaults and password == demo_defaults.get("password"):
            repo._seed_user(
                username,
                password,
                otp_secret=record.otp_secret,
                active=bool(record.active),
            )
        else:
            repo.record_failure(username)
            return None
    if not UserRepository.verify_otp(record.otp_secret, otp):
        return None
    repo.reset_failures(username)
    return User(username=username, active=True)


def create_access_token(data: Dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Return a signed JWT access token with a unique JTI for revocation support."""
    from . import ALGORITHM, SECRET_KEY, TOKEN_AUDIENCE, TOKEN_ISSUER

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    username = data.get("sub")
    generation = 0
    if username:
        try:
            generation = _get_user_repository().get_token_generation(str(username))
        except Exception:
            generation = 0
    to_encode.update(
        {
            "exp": expire,
            "iss": TOKEN_ISSUER,
            "aud": TOKEN_AUDIENCE,
            "jti": secrets.token_hex(16),
            "gen": generation,
        }
    )
    return str(jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM))


def _access_token_lifetime_seconds() -> int:
    """Return the configured access-token lifetime in whole seconds."""
    from . import ACCESS_TOKEN_EXPIRE_MINUTES

    return max(1, int(ACCESS_TOKEN_EXPIRE_MINUTES) * 60)


def _refresh_token_lifetime() -> timedelta:
    """Return the configured refresh-token lifetime."""
    from . import REFRESH_TOKEN_EXPIRE_DAYS

    return timedelta(days=max(1, int(REFRESH_TOKEN_EXPIRE_DAYS)))


def _build_access_token_response(
    *,
    username: str,
    refresh_token: str | None = None,
) -> Token:
    """Build a token response with the current access-token lifetime."""
    expires_in = _access_token_lifetime_seconds()
    access_token = create_access_token({"sub": username}, timedelta(seconds=expires_in))
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in,
        refresh_token=refresh_token,
    )


def _issue_refresh_token(*, username: str, family_id: str | None = None) -> tuple[str, str, datetime]:
    """Create and persist a long-lived refresh token for ``username``."""
    repo = _get_user_repository()
    token = secrets.token_urlsafe(48)
    resolved_family_id = family_id or secrets.token_hex(16)
    expires_at = datetime.now(timezone.utc) + _refresh_token_lifetime()
    repo.store_refresh_token(
        username=username,
        token=token,
        family_id=resolved_family_id,
        expires_at=expires_at,
    )
    return token, resolved_family_id, expires_at


def _authenticate_login_user(
    *,
    username: str,
    password: str,
    otp: str = "",
) -> User:
    """Authenticate a username/password pair, including MFA and LDAP fallback."""
    from . import REQUIRE_MFA

    if REQUIRE_MFA:
        user = authenticate_mfa(username, password, otp)
    else:
        user = authenticate_user(username, password)

    if not user:
        try:
            from .. import ldap_auth as _ldap_auth  # noqa: PLC0415

            if _ldap_auth.ldap_enabled():
                ldap_result = _ldap_auth.ldap_login(username, password)
                if ldap_result:
                    ldap_username, ldap_roles = ldap_result
                    repo = _get_user_repository()
                    if repo.get_user(ldap_username) is None:
                        import secrets as _sec

                        repo._seed_user(ldap_username, _sec.token_hex(32), active=True)
                    if ldap_roles:
                        try:
                            from .. import rbac as _rbac  # noqa: PLC0415

                            for role_name in ldap_roles:
                                _rbac.add_role(ldap_username, role_name)
                        except Exception:  # pragma: no cover
                            pass
                    user = User(username=ldap_username, active=True)
        except Exception:  # pragma: no cover — ldap3 may not be installed
            pass

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username, password, or OTP",
        )
    return user


def login_for_credentials(
    *,
    username: str,
    password: str,
    otp: str = "",
) -> Token:
    """Issue an access-token pair for explicit credential fields."""
    user = _authenticate_login_user(username=username, password=password, otp=otp)
    refresh_token, _, _ = _issue_refresh_token(username=user.username)
    return _build_access_token_response(username=user.username, refresh_token=refresh_token)


def login_for_oidc_credentials(
    *,
    username: str,
    password: str,
    otp: str = "",
) -> Token:
    """Issue an OIDC token for explicit credential fields."""
    from . import OIDC_TOKEN_EXPIRE_MINUTES

    user = _authenticate_login_user(username=username, password=password, otp=otp)
    id_token = create_id_token(
        {"sub": user.username},
        timedelta(minutes=OIDC_TOKEN_EXPIRE_MINUTES),
    )
    return Token(
        access_token=id_token,
        token_type="bearer",
        expires_in=max(1, int(OIDC_TOKEN_EXPIRE_MINUTES) * 60),
    )


def refresh_access_token(refresh_token: str) -> Token:
    """Rotate a refresh token and return a fresh access-token pair."""
    repo = _get_user_repository()
    record = repo.get_refresh_token(refresh_token)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    now = datetime.now(timezone.utc)
    if record.expires_at <= now:
        repo.revoke_refresh_token_family(record.family_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired",
        )
    if record.revoked_at is not None or record.rotated_at is not None:
        repo.revoke_refresh_token_family(record.family_id)
        repo.bump_token_generation(record.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token reuse detected; session revoked",
        )
    user = repo.get_user(record.username)
    if user is None or not user.active:
        repo.revoke_refresh_token_family(record.family_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    next_refresh_token = secrets.token_urlsafe(48)
    next_expires_at = now + _refresh_token_lifetime()
    repo.rotate_refresh_token(token=refresh_token, replaced_by_token=next_refresh_token)
    repo.store_refresh_token(
        username=record.username,
        token=next_refresh_token,
        family_id=record.family_id,
        expires_at=next_expires_at,
        parent_token=refresh_token,
    )
    return _build_access_token_response(
        username=record.username,
        refresh_token=next_refresh_token,
    )


def create_id_token(data: Dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Return an ID token for OIDC authentication."""
    from . import OIDC_ALGORITHM, OIDC_SECRET_KEY, OIDC_TOKEN_AUDIENCE, OIDC_TOKEN_ISSUER

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update(
        {
            "exp": expire,
            "iss": OIDC_TOKEN_ISSUER,
            "aud": OIDC_TOKEN_AUDIENCE,
        }
    )
    return str(jwt.encode(to_encode, OIDC_SECRET_KEY, algorithm=OIDC_ALGORITHM))


def _require_csrf_token(request: Request) -> None:
    """Ensure the request presents a valid CSRF token when using cookie auth."""
    csrf_cookie = request.cookies.get("csrf_token")
    csrf_header = request.headers.get("X-CSRF-Token")
    if not csrf_cookie or not csrf_header:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing CSRF token",
        )
    if not secrets.compare_digest(str(csrf_cookie), str(csrf_header)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid CSRF token",
        )


def get_current_user(request: Request, token: str | None = Depends(oauth2_scheme)) -> User:
    from . import (
        ALGORITHM,
        DEMO_USER_DEFAULTS,
        SECRET_KEY,
        SECRET_KEY_PREVIOUS,
        TOKEN_AUDIENCE,
        TOKEN_ISSUER,
        _allow_demo_seed,
        _password_policy,
    )

    cookie_token = request.cookies.get("access_token")
    if not token and cookie_token:
        _require_csrf_token(request)
        token = cookie_token
    elif not token:
        token = cookie_token
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    try:
        _decode_kwargs = {
            "algorithms": [ALGORITHM],
            "audience": TOKEN_AUDIENCE,
            "issuer": TOKEN_ISSUER,
        }
        try:
            payload = jwt.decode(token, SECRET_KEY, **_decode_kwargs)
        except JWTError:
            if SECRET_KEY_PREVIOUS is None:
                raise
            payload = jwt.decode(token, SECRET_KEY_PREVIOUS, **_decode_kwargs)
        username: str | None = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        jti: str | None = payload.get("jti")
        if jti and is_token_revoked(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked"
            )
        if jti:
            try:
                from ..oidc_client import touch_session as _touch_session

                if not _touch_session(jti):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Session expired due to inactivity — please log in again",
                    )
            except HTTPException:
                raise
            except Exception:  # pragma: no cover — best effort
                pass
        token_gen: int = int(payload.get("gen", 0))
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc
    repo = _get_user_repository()
    record = repo.get_user(username)
    if record is None:
        demo_defaults = DEMO_USER_DEFAULTS.get(username)
        if demo_defaults and _allow_demo_seed():
            repo._seed_user(
                username,
                demo_defaults["password"],
                otp_secret=demo_defaults.get("otp_secret"),
                active=True,
            )
            record = repo.get_user(username)
    if not record or not record.active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    if token_gen < record.token_generation:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session invalidated — please log in again",
        )
    policy = _password_policy()
    if policy.max_age_days > 0 and repo.is_password_expired(username, policy.max_age_days):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="password_expired",
        )
    return User(username=username, active=True)


async def _extract_otp(request: Request | None) -> str:
    """Return the submitted one-time password if present."""
    if request is None:
        return ""
    form = await request.form()
    otp = form.get("otp")
    return str(otp or "")


async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    request: Request | None = None,
) -> Token:
    """Issue a short-lived JWT bearer token."""
    otp = await _extract_otp(request)
    return login_for_credentials(
        username=form_data.username,
        password=form_data.password,
        otp=otp,
    )


async def login_for_oidc_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    request: Request | None = None,
) -> Token:
    """Return an ID token for valid credentials using a separate secret."""
    otp = await _extract_otp(request)
    return login_for_oidc_credentials(
        username=form_data.username,
        password=form_data.password,
        otp=otp,
    )


def get_current_user_oidc(
    request: Request, token: str | None = Depends(oidc_scheme)
) -> User:
    """Validate ID token and return the associated user."""
    from . import (
        DEMO_USER_DEFAULTS,
        OIDC_ALGORITHM,
        OIDC_SECRET_KEY,
        OIDC_SECRET_KEY_PREVIOUS,
        OIDC_TOKEN_AUDIENCE,
        OIDC_TOKEN_ISSUER,
        _allow_demo_seed,
    )

    cookie_token = request.cookies.get("access_token")
    if not token and cookie_token:
        _require_csrf_token(request)
        token = cookie_token
    elif not token:
        token = cookie_token
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    try:
        decode_kwargs = {
            "algorithms": [OIDC_ALGORITHM],
            "audience": OIDC_TOKEN_AUDIENCE,
            "issuer": OIDC_TOKEN_ISSUER,
        }
        try:
            payload = jwt.decode(token, OIDC_SECRET_KEY, **decode_kwargs)
        except JWTError:
            if OIDC_SECRET_KEY_PREVIOUS is None:
                raise
            payload = jwt.decode(token, OIDC_SECRET_KEY_PREVIOUS, **decode_kwargs)
        username: str | None = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc
    repo = _get_user_repository()
    record = repo.get_user(username)
    if record is None:
        demo_defaults = DEMO_USER_DEFAULTS.get(username)
        if demo_defaults and _allow_demo_seed():
            repo._seed_user(
                username,
                demo_defaults["password"],
                otp_secret=demo_defaults.get("otp_secret"),
                active=True,
            )
            record = repo.get_user(username)
    if not record or not record.active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    return User(username=username, active=True)


def configure_user_repository(path: str | os.PathLike[str]) -> None:
    """Replace the active user repository with one backed by ``path``."""
    os.environ["DOCREVIEW360_USER_DB"] = str(path)
    _get_user_repository()

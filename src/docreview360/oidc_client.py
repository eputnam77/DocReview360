# SPDX-License-Identifier: MIT
"""OIDC/OAuth 2.0 Authorization Code + PKCE client for DocReview360.

DocReview360 acts as an *RP (relying party)* — it delegates authentication to
an external OIDC provider (Keycloak, Auth0, Azure AD, Okta, etc.) and issues
its own session JWT after the provider validates the user.

Configuration (environment variables)
--------------------------------------
OIDC_PROVIDER_URL       Base URL of the OIDC provider, e.g.
                        ``https://keycloak.example.com/realms/docreview360``.
                        The module appends ``/.well-known/openid-configuration``
                        to discover all endpoints.
OIDC_CLIENT_ID          OAuth 2.0 client_id registered with the provider.
OIDC_CLIENT_SECRET      OAuth 2.0 client_secret (confidential client only).
                        Leave empty for public clients — PKCE is always used.
OIDC_REDIRECT_URI       Full URI the provider should redirect to after login,
                        e.g. ``https://app.example.com/oidc/callback``.
OIDC_SCOPES             Space-separated list of scopes (default: ``openid profile email``).
OIDC_ENABLED            Set to ``"true"`` to enable OIDC login.  Defaults to
                        ``"false"`` so existing local-auth flows are unchanged.
OIDC_SESSION_MAX_CONCURRENT   Maximum simultaneous sessions per user (default: 5).
OIDC_IDLE_TIMEOUT_MINUTES     Idle-timeout in minutes; 0 = disabled (default: 60).

Keycloak-specific variables (see ``keycloak_auth.py`` for full documentation)
------------------------------------------------------------------------------
KEYCLOAK_REALM_ROLES_CLAIM    Top-level claim key for realm roles (default: ``"realm_access"``).
KEYCLOAK_CLIENT_ID_FOR_ROLES  Client-id whose ``resource_access`` roles to map
                              (defaults to ``OIDC_CLIENT_ID``).
KEYCLOAK_ROLE_MAP             JSON object mapping Keycloak role names to DocReview360 roles.
KEYCLOAK_DEFAULT_ROLE         Fallback role when no mapping matches (default: ``"reviewer"``).
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OIDC_ENABLED: bool = os.getenv("OIDC_ENABLED", "false").strip().lower() in {
    "1", "true", "yes", "on"
}
OIDC_PROVIDER_URL: str = os.getenv("OIDC_PROVIDER_URL", "").rstrip("/")
OIDC_CLIENT_ID: str = os.getenv("OIDC_CLIENT_ID", "")
OIDC_CLIENT_SECRET: str = os.getenv("OIDC_CLIENT_SECRET", "")
OIDC_REDIRECT_URI: str = os.getenv("OIDC_REDIRECT_URI", "")
OIDC_SCOPES: str = os.getenv("OIDC_SCOPES", "openid profile email")
SESSION_MAX_CONCURRENT: int = int(os.getenv("OIDC_SESSION_MAX_CONCURRENT", "5"))
IDLE_TIMEOUT_MINUTES: int = int(os.getenv("OIDC_IDLE_TIMEOUT_MINUTES", "60"))

# ---------------------------------------------------------------------------
# PKCE helpers
# ---------------------------------------------------------------------------


def generate_pkce_pair() -> tuple[str, str]:
    """Return ``(code_verifier, code_challenge)`` using S256 method.

    The verifier is a 96-byte URL-safe random string (~128 chars).
    The challenge is the URL-safe base64 encoding of its SHA-256 digest.
    """
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(96)).rstrip(b"=").decode("ascii")
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


# ---------------------------------------------------------------------------
# Provider discovery cache
# ---------------------------------------------------------------------------

_discovery_cache: dict[str, Any] = {}


def _get_discovery(provider_url: str) -> dict[str, Any]:
    """Fetch and cache the OIDC provider discovery document."""
    if provider_url in _discovery_cache:
        return _discovery_cache[provider_url]

    import httpx

    discovery_url = f"{provider_url}/.well-known/openid-configuration"
    _logger.info("Fetching OIDC discovery document from %s", discovery_url)
    try:
        resp = httpx.get(discovery_url, timeout=10.0)
        resp.raise_for_status()
        doc = resp.json()
        _discovery_cache[provider_url] = doc
        return doc
    except Exception as exc:
        raise RuntimeError(
            f"Failed to fetch OIDC discovery document from {discovery_url}: {exc}"
        ) from exc


def get_authorization_endpoint() -> str:
    """Return the provider's authorization endpoint URL."""
    doc = _get_discovery(OIDC_PROVIDER_URL)
    return str(doc["authorization_endpoint"])


def get_token_endpoint() -> str:
    """Return the provider's token endpoint URL."""
    doc = _get_discovery(OIDC_PROVIDER_URL)
    return str(doc["token_endpoint"])


def get_jwks_uri() -> str:
    """Return the provider's JWKS URI for ID token signature validation."""
    doc = _get_discovery(OIDC_PROVIDER_URL)
    return str(doc["jwks_uri"])


def get_issuer() -> str:
    """Return the expected issuer claim from the discovery document."""
    doc = _get_discovery(OIDC_PROVIDER_URL)
    return str(doc["issuer"])


# ---------------------------------------------------------------------------
# Authorization URL generation
# ---------------------------------------------------------------------------


def build_authorization_url(
    redirect_uri: str | None = None,
    extra_params: dict[str, str] | None = None,
) -> tuple[str, str, str, str]:
    """Build an authorization URL for the OIDC Authorization Code + PKCE flow.

    Returns
    -------
    (authorization_url, state, nonce, code_verifier)
        ``state`` and ``nonce`` must be stored server-side and validated on
        callback.  ``code_verifier`` must be stored and sent in the token
        exchange.
    """
    if not OIDC_PROVIDER_URL or not OIDC_CLIENT_ID:
        raise RuntimeError(
            "OIDC_PROVIDER_URL and OIDC_CLIENT_ID must be set to use OIDC login"
        )

    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    code_verifier, code_challenge = generate_pkce_pair()

    params: dict[str, str] = {
        "response_type": "code",
        "client_id": OIDC_CLIENT_ID,
        "redirect_uri": redirect_uri or OIDC_REDIRECT_URI,
        "scope": OIDC_SCOPES,
        "state": state,
        "nonce": nonce,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    if extra_params:
        params.update(extra_params)

    auth_endpoint = get_authorization_endpoint()
    from urllib.parse import urlencode
    authorization_url = f"{auth_endpoint}?{urlencode(params)}"

    return authorization_url, state, nonce, code_verifier


# ---------------------------------------------------------------------------
# State record persistence
# ---------------------------------------------------------------------------


def _get_db():  # type: ignore[return]
    from .db_store import get_db
    return get_db()


def store_oidc_state(
    state: str,
    nonce: str,
    code_verifier: str,
    redirect_uri: str | None = None,
    ttl_seconds: int = 600,
) -> None:
    """Persist an OIDC in-flight state record in the database."""
    from sqlalchemy import text as _text
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=ttl_seconds)
    db = _get_db()
    with db.session() as conn:
        conn.execute(
            _text(
                "INSERT INTO oidc_states (state, nonce, code_verifier, redirect_uri, created_at, expires_at)"
                " VALUES (:state, :nonce, :cv, :ruri, :now, :exp)"
                " ON CONFLICT(state) DO UPDATE SET expires_at=excluded.expires_at"
            ),
            {
                "state": state,
                "nonce": nonce,
                "cv": code_verifier,
                "ruri": redirect_uri,
                "now": now.isoformat(),
                "exp": expires_at.isoformat(),
            },
        )


def consume_oidc_state(state: str) -> dict[str, str] | None:
    """Look up and delete an OIDC state record, returning its data or None if invalid/expired."""
    from sqlalchemy import text as _text
    db = _get_db()
    now = datetime.now(timezone.utc)
    with db.session() as conn:
        row = conn.execute(
            _text(
                "SELECT nonce, code_verifier, redirect_uri, expires_at"
                " FROM oidc_states WHERE state = :state"
            ),
            {"state": state},
        ).fetchone()
        if row is None:
            return None
        conn.execute(_text("DELETE FROM oidc_states WHERE state = :state"), {"state": state})

    nonce, code_verifier, redirect_uri, expires_raw = row
    # Parse and compare expiry
    try:
        if isinstance(expires_raw, str):
            expires_at = datetime.fromisoformat(expires_raw)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
        else:
            expires_at = expires_raw
        if now > expires_at:
            return None
    except (ValueError, TypeError):
        return None

    return {"nonce": nonce, "code_verifier": code_verifier, "redirect_uri": redirect_uri or ""}


# ---------------------------------------------------------------------------
# Token exchange
# ---------------------------------------------------------------------------


def exchange_code_for_tokens(
    code: str,
    code_verifier: str,
    redirect_uri: str | None = None,
) -> dict[str, Any]:
    """Exchange an authorization code for tokens at the provider's token endpoint.

    Returns the raw token response dict (includes ``id_token``, ``access_token``, etc.).
    """
    import httpx

    token_endpoint = get_token_endpoint()
    data: dict[str, str] = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri or OIDC_REDIRECT_URI,
        "client_id": OIDC_CLIENT_ID,
        "code_verifier": code_verifier,
    }
    auth = None
    if OIDC_CLIENT_SECRET:
        # Confidential client: use HTTP Basic auth
        auth = (OIDC_CLIENT_ID, OIDC_CLIENT_SECRET)
        data.pop("client_id")

    _logger.debug("Exchanging OIDC code at %s", token_endpoint)
    try:
        resp = httpx.post(token_endpoint, data=data, auth=auth, timeout=15.0)
        resp.raise_for_status()
    except Exception as exc:
        raise RuntimeError(f"Token exchange failed: {exc}") from exc

    return resp.json()


# ---------------------------------------------------------------------------
# ID token validation
# ---------------------------------------------------------------------------


def validate_id_token(
    id_token: str,
    nonce: str,
    *,
    audience: str | None = None,
) -> dict[str, Any]:
    """Validate an OIDC ID token and return its claims.

    Validates:
    - Signature using provider JWKS
    - ``iss`` matches the discovery issuer
    - ``aud`` contains our client_id (or the provided audience)
    - ``nonce`` matches the stored value (replay prevention)
    - ``exp`` / ``iat`` (handled by python-jose)
    """
    from jose import jwt as _jwt

    jwks_uri = get_jwks_uri()
    expected_issuer = get_issuer()
    expected_audience = audience or OIDC_CLIENT_ID

    # Fetch JWKS (cached per discovery document; in production use a TTL cache)
    import httpx
    try:
        jwks_resp = httpx.get(jwks_uri, timeout=10.0)
        jwks_resp.raise_for_status()
        jwks = jwks_resp.json()
    except Exception as exc:
        raise RuntimeError(f"Failed to fetch JWKS from {jwks_uri}: {exc}") from exc

    try:
        claims = _jwt.decode(
            id_token,
            jwks,
            algorithms=["RS256", "ES256", "RS384", "ES384", "RS512"],
            audience=expected_audience,
            issuer=expected_issuer,
        )
    except Exception as exc:
        raise ValueError(f"ID token validation failed: {exc}") from exc

    if claims.get("nonce") != nonce:
        raise ValueError("ID token nonce mismatch — possible replay attack")

    return claims


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------


def create_user_session(
    username: str,
    jti: str,
    expires_at: datetime,
    auth_method: str = "password",
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> str:
    """Record a new user session and enforce concurrent session limits.

    Returns the new session_id.  If the user already has ``SESSION_MAX_CONCURRENT``
    active sessions the oldest one is revoked to make room.
    """
    from sqlalchemy import text as _text

    from . import auth as _auth

    db = _get_db()
    now = datetime.now(timezone.utc)
    session_id = str(uuid4())

    with db.session() as conn:
        # Count active non-expired sessions for this user
        rows = conn.execute(
            _text(
                "SELECT id, jti, expires_at FROM user_sessions"
                " WHERE username = :username AND is_active = 1"
                " ORDER BY last_active_at ASC"
            ),
            {"username": username},
        ).fetchall()

        # Expire stale sessions
        valid_sessions = []
        for row in rows:
            sid, row_jti, exp_raw = row
            try:
                if isinstance(exp_raw, str):
                    exp_dt = datetime.fromisoformat(exp_raw)
                    if exp_dt.tzinfo is None:
                        exp_dt = exp_dt.replace(tzinfo=timezone.utc)
                else:
                    exp_dt = exp_raw
                if now < exp_dt:
                    valid_sessions.append((sid, row_jti))
                else:
                    conn.execute(
                        _text("UPDATE user_sessions SET is_active = 0 WHERE id = :sid"),
                        {"sid": sid},
                    )
            except (ValueError, TypeError):
                conn.execute(
                    _text("UPDATE user_sessions SET is_active = 0 WHERE id = :sid"),
                    {"sid": sid},
                )

        # Revoke oldest sessions if at limit
        while len(valid_sessions) >= SESSION_MAX_CONCURRENT:
            oldest_sid, oldest_jti = valid_sessions.pop(0)
            conn.execute(
                _text("UPDATE user_sessions SET is_active = 0 WHERE id = :sid"),
                {"sid": oldest_sid},
            )
            _logger.info(
                "Revoked oldest session %s for user %r (concurrent limit %d)",
                oldest_sid, username, SESSION_MAX_CONCURRENT,
            )
            # Also revoke the JWT so existing tokens fail
            try:
                _auth.revoke_token(oldest_jti, expires_at)
            except Exception:  # pragma: no cover - best effort
                pass

        # Insert new session
        conn.execute(
            _text(
                "INSERT INTO user_sessions"
                " (id, username, jti, created_at, last_active_at, expires_at,"
                "  ip_address, user_agent, is_active, auth_method)"
                " VALUES (:id, :un, :jti, :now, :now, :exp, :ip, :ua, 1, :method)"
            ),
            {
                "id": session_id,
                "un": username,
                "jti": jti,
                "now": now.isoformat(),
                "exp": expires_at.isoformat(),
                "ip": ip_address,
                "ua": user_agent,
                "method": auth_method,
            },
        )

    return session_id


def touch_session(jti: str) -> bool:
    """Update last_active_at for the session and check idle timeout.

    Returns False if the session has exceeded the idle timeout and should be
    treated as expired (the caller should reject the request).
    """
    if IDLE_TIMEOUT_MINUTES <= 0:
        return True

    from sqlalchemy import text as _text

    db = _get_db()
    now = datetime.now(timezone.utc)

    with db.session() as conn:
        row = conn.execute(
            _text(
                "SELECT id, last_active_at FROM user_sessions"
                " WHERE jti = :jti AND is_active = 1"
            ),
            {"jti": jti},
        ).fetchone()

        if row is None:
            return True  # No session record — let normal JWT validation handle it

        sid, last_active_raw = row
        try:
            if isinstance(last_active_raw, str):
                last_active = datetime.fromisoformat(last_active_raw)
                if last_active.tzinfo is None:
                    last_active = last_active.replace(tzinfo=timezone.utc)
            else:
                last_active = last_active_raw
        except (ValueError, TypeError):
            return True

        idle_seconds = (now - last_active).total_seconds()
        if idle_seconds > IDLE_TIMEOUT_MINUTES * 60:
            # Revoke the session
            conn.execute(
                _text("UPDATE user_sessions SET is_active = 0 WHERE id = :sid"),
                {"sid": sid},
            )
            _logger.info(
                "Session %s expired due to idle timeout (%.0fs > %ds)",
                sid, idle_seconds, IDLE_TIMEOUT_MINUTES * 60,
            )
            return False

        # Update last active timestamp
        conn.execute(
            _text("UPDATE user_sessions SET last_active_at = :now WHERE id = :sid"),
            {"now": now.isoformat(), "sid": sid},
        )
        return True


def revoke_user_session(jti: str) -> None:
    """Mark a session inactive (used on logout)."""
    from sqlalchemy import text as _text

    db = _get_db()
    with db.session() as conn:
        conn.execute(
            _text("UPDATE user_sessions SET is_active = 0 WHERE jti = :jti"),
            {"jti": jti},
        )


def list_user_sessions(username: str) -> list[dict[str, Any]]:
    """Return active sessions for ``username`` (for admin/user self-service)."""
    from sqlalchemy import text as _text

    db = _get_db()
    now = datetime.now(timezone.utc)
    with db.session() as conn:
        rows = conn.execute(
            _text(
                "SELECT id, jti, created_at, last_active_at, expires_at,"
                "       ip_address, user_agent, auth_method"
                " FROM user_sessions"
                " WHERE username = :username AND is_active = 1"
                " ORDER BY last_active_at DESC"
            ),
            {"username": username},
        ).fetchall()

    result = []
    expired_session_ids: list[str] = []
    for row in rows:
        sid, jti, created_raw, last_active_raw, expires_raw, ip, ua, method = row
        try:
            if isinstance(expires_raw, str):
                expires_at = datetime.fromisoformat(expires_raw)
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
            else:
                expires_at = expires_raw
        except (ValueError, TypeError):
            expired_session_ids.append(sid)
            continue
        if now >= expires_at:
            expired_session_ids.append(sid)
            continue
        result.append(
            {
                "session_id": sid,
                "jti": jti,
                "created_at": str(created_raw),
                "last_active_at": str(last_active_raw),
                "expires_at": str(expires_at),
                "ip_address": ip,
                "user_agent": ua,
                "auth_method": method,
            }
        )
    if expired_session_ids:
        with db.session() as conn:
            for sid in expired_session_ids:
                conn.execute(
                    _text("UPDATE user_sessions SET is_active = 0 WHERE id = :sid"),
                    {"sid": sid},
                )
    return result

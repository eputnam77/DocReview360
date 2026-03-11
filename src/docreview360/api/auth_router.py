# SPDX-License-Identifier: MIT
"""Auth sub-router: /token, /oidc/*, /me, /logout, /login, /dashboard, /help, /."""
from __future__ import annotations

import hashlib
import hmac
import logging
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from markdown_it import MarkdownIt

from .. import auth
from .. import oidc_client
from ..logs import log_event
from ..messages import render

_logger = logging.getLogger(__name__)

router = APIRouter()

# Templates are stored one level above this module in ``docreview360/templates``.
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

_SESSION_COOKIE_MAX_AGE: int = auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60


def _request_source(request: Request) -> str:
    """Return a stable source identifier for request-scoped rate limiting."""
    forwarded_for = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if forwarded_for:
        return forwarded_for
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _encode_session_cookie(username: str) -> str:
    """Return a signed session cookie value for ``username``."""
    issued_at = int(time.time())
    payload = f"{username}:{issued_at}"
    signature = hmac.new(
        auth.SECRET_KEY.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}:{signature}"


def _decode_session_cookie(value: str | None) -> str | None:
    """Return the validated username from a session cookie value."""
    if not value:
        return None
    try:
        username, issued_raw, provided_sig = value.rsplit(":", 2)
        issued_at = int(issued_raw)
    except (TypeError, ValueError):
        return None
    payload = f"{username}:{issued_at}"
    expected_sig = hmac.new(
        auth.SECRET_KEY.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected_sig, provided_sig):
        return None
    if int(time.time()) - issued_at > _SESSION_COOKIE_MAX_AGE:
        return None
    return username or None


def _get_rate_limiters() -> tuple[Any, Any]:
    """Return (token_limiter, login_limiter) from the parent package at call time."""
    import docreview360.api as _api_mod
    return _api_mod._TOKEN_RATE_LIMITER, _api_mod._LOGIN_RATE_LIMITER


@router.post("/token", response_model=auth.Token)
async def token(
    request: Request, response: Response, form_data: OAuth2PasswordRequestForm = Depends()
) -> auth.Token:
    """Return a JWT access token for valid user credentials."""
    token_limiter, _ = _get_rate_limiters()
    token_key = f"token:{form_data.username.strip().lower()}:{_request_source(request)}"
    token_limiter.enforce(token_key)
    token_resp = await auth.login_for_access_token(form_data, request)
    response.set_cookie(
        "access_token",
        token_resp.access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    log_event(
        "login",
        user_id=form_data.username,
        message=render("login", user=form_data.username),
    )
    # Record the session for concurrent-limit and idle-timeout enforcement
    try:
        from jose import jwt as _jwt
        payload = _jwt.decode(
            token_resp.access_token,
            auth.SECRET_KEY,
            algorithms=[auth.ALGORITHM],
            audience=auth.TOKEN_AUDIENCE,
            issuer=auth.TOKEN_ISSUER,
        )
        jti = payload.get("jti")
        exp_ts = payload.get("exp")
        if jti and exp_ts:
            from datetime import datetime, timezone as _tz
            expires_at = datetime.fromtimestamp(exp_ts, tz=_tz.utc)
            ip = _request_source(request)
            ua = request.headers.get("user-agent")
            oidc_client.create_user_session(
                username=form_data.username,
                jti=jti,
                expires_at=expires_at,
                auth_method="mfa" if auth.REQUIRE_MFA else "password",
                ip_address=ip,
                user_agent=ua,
            )
    except Exception as _sess_exc:  # pragma: no cover - best effort
        _logger.debug("Session record creation failed (non-fatal): %s", _sess_exc)
    return token_resp


@router.post("/oidc/token", response_model=auth.Token)
async def oidc_token(
    request: Request, form_data: OAuth2PasswordRequestForm = Depends()
) -> auth.Token:
    """Return an ID token using the OIDC flow."""
    return await auth.login_for_oidc_token(form_data, request)


@router.get("/me")
async def read_current_user(current_user: auth.User = Depends(auth.get_current_user)) -> auth.User:
    """Return the authenticated user."""
    return current_user


@router.get("/users/search")
async def search_users(
    q: str = Query(default="", description="Search term (username prefix / substring)"),
    limit: int = Query(default=10, ge=1, le=50, description="Maximum results to return"),
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[dict]:
    """Typeahead user search across username.

    Returns up to *limit* matching users with username, display_name, and active flag.
    Accessible to all authenticated users; used by the UserPicker component.
    """
    repo = auth._get_user_repository()
    all_users = repo.list_users()
    term = q.strip().lower()
    results = []
    for user in all_users:
        if not term or term in user.username.lower():
            results.append(
                {
                    "username": user.username,
                    "display_name": user.username,
                    "active": bool(user.active),
                }
            )
        if len(results) >= limit:
            break
    return results


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    token: str | None = Depends(auth.oauth2_scheme),
) -> dict[str, str]:
    """Clear authentication cookie and revoke the current JWT."""
    active_token = token or request.cookies.get("access_token")
    if active_token:
        try:
            from jose import jwt as _jwt

            payload = _jwt.decode(
                active_token,
                auth.SECRET_KEY,
                algorithms=[auth.ALGORITHM],
                audience=auth.TOKEN_AUDIENCE,
                issuer=auth.TOKEN_ISSUER,
            )
            jti = payload.get("jti")
            exp_ts = payload.get("exp")
            if jti and exp_ts:
                from datetime import datetime, timezone

                expires_at = datetime.fromtimestamp(exp_ts, tz=timezone.utc)
                auth.revoke_token(jti, expires_at)
                # Also mark the session inactive
                oidc_client.revoke_user_session(jti)
        except Exception as exc:  # noqa: BLE001 — best-effort revocation
            _logger.warning("Token revocation failed during logout: %s", exc)
    response.delete_cookie("access_token")
    response.delete_cookie("csrf_token")
    response.delete_cookie("session")
    return {"detail": "Logged out"}


@router.get("/oidc/me")
async def read_current_oidc_user(
    current_user: auth.User = Depends(auth.get_current_user_oidc),
) -> auth.User:
    """Return the authenticated user for the OIDC flow."""
    return current_user


@router.get("/", response_class=HTMLResponse)
async def root(request: Request) -> HTMLResponse:
    """Display login page or dashboard depending on session."""
    session_user = _decode_session_cookie(request.cookies.get("session"))
    if session_user:
        return templates.TemplateResponse(request, "dashboard.html", {"user": session_user})
    return templates.TemplateResponse(request, "login.html")


@router.post("/login", response_class=HTMLResponse)
async def login(request: Request, username: str = Form(...), password: str = Form(...)) -> Response:
    """Validate credentials and create a hardened session cookie."""
    _, login_limiter = _get_rate_limiters()
    login_key = f"login:{username.strip().lower()}:{_request_source(request)}"
    login_limiter.enforce(login_key)
    if auth.authenticate_user(username, password):
        response = RedirectResponse("/projects", status_code=303)
        response.set_cookie(
            "session",
            _encode_session_cookie(username),
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=_SESSION_COOKIE_MAX_AGE,
        )
        log_event(
            "login",
            user_id=username,
            message=render("login", user=username),
        )
        return response
    return templates.TemplateResponse(
        request, "login.html", {"error": "Invalid credentials"}, status_code=400
    )


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request) -> Response:
    """Placeholder dashboard displayed after login."""
    session_user = _decode_session_cookie(request.cookies.get("session"))
    if not session_user:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "dashboard.html", {"user": session_user})


@router.get("/help", response_class=HTMLResponse)
async def help_page() -> HTMLResponse:
    """Display a lightweight help page rendered from Markdown."""
    doc_path = Path(__file__).resolve().parent.parent.parent.parent / "docs" / "getting_started.md"
    try:
        text = doc_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=500, detail="Unable to load documentation") from exc
    html = MarkdownIt().render(text)
    return HTMLResponse(html)


# ---------------------------------------------------------------------------
# OIDC Authorization Code + PKCE endpoints
# ---------------------------------------------------------------------------


@router.get("/oidc/authorize")
async def oidc_authorize(
    request: Request,
    redirect_uri: str | None = Query(default=None),
) -> RedirectResponse:
    """Initiate an OIDC Authorization Code + PKCE flow.

    Generates a ``state``, ``nonce``, and PKCE pair, stores them in the
    database, then redirects the browser to the external identity provider.
    Set ``OIDC_ENABLED=true`` and the provider vars to activate.
    """
    if not oidc_client.OIDC_ENABLED:
        raise HTTPException(status_code=404, detail="OIDC login is not enabled on this server")
    try:
        auth_url, state, nonce, code_verifier = oidc_client.build_authorization_url(
            redirect_uri=redirect_uri
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    oidc_client.store_oidc_state(
        state=state,
        nonce=nonce,
        code_verifier=code_verifier,
        redirect_uri=redirect_uri,
    )
    _logger.debug("OIDC authorize redirect → %s", auth_url[:80])
    return RedirectResponse(auth_url, status_code=302)


@router.get("/oidc/callback")
async def oidc_callback(
    request: Request,
    response: Response,
    code: str = Query(...),
    state: str = Query(...),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
) -> Any:
    """Handle the OIDC provider callback.

    Validates ``state`` and ``nonce``, exchanges the authorization ``code``
    for tokens, validates the ID token, then issues a DocReview360 JWT and
    redirects the user to the dashboard.
    """
    if not oidc_client.OIDC_ENABLED:
        raise HTTPException(status_code=404, detail="OIDC login is not enabled on this server")

    if error:
        _logger.warning("OIDC provider returned error: %s — %s", error, error_description)
        raise HTTPException(
            status_code=400,
            detail=f"OIDC provider error: {error}. {error_description or ''}".strip(),
        )

    # Validate and consume state (prevents CSRF)
    state_data = oidc_client.consume_oidc_state(state)
    if state_data is None:
        raise HTTPException(status_code=400, detail="Invalid or expired OIDC state parameter")

    nonce = state_data["nonce"]
    code_verifier = state_data["code_verifier"]
    stored_redirect_uri = state_data.get("redirect_uri") or None

    # Exchange code for tokens
    try:
        token_response = oidc_client.exchange_code_for_tokens(
            code=code,
            code_verifier=code_verifier,
            redirect_uri=stored_redirect_uri,
        )
    except RuntimeError as exc:
        _logger.error("OIDC token exchange failed: %s", exc)
        raise HTTPException(status_code=502, detail="Failed to exchange code with identity provider")

    id_token = token_response.get("id_token")
    if not id_token:
        raise HTTPException(status_code=502, detail="Identity provider did not return an ID token")

    # Validate ID token and extract claims
    try:
        claims = oidc_client.validate_id_token(id_token, nonce)
    except ValueError as exc:
        _logger.warning("ID token validation failed: %s", exc)
        raise HTTPException(status_code=401, detail="ID token validation failed")

    # Extract username and roles from claims.
    # When the provider is Keycloak, use its specialised claim extractor which
    # reads realm_access.roles / resource_access.<client>.roles and applies
    # KEYCLOAK_ROLE_MAP / KEYCLOAK_DEFAULT_ROLE.
    from .. import keycloak_auth as _kc

    if _kc.is_keycloak_provider(oidc_client.OIDC_PROVIDER_URL):
        _logger.debug("Keycloak provider detected — using Keycloak claim extractor")
        user_info = _kc.get_user_info_from_keycloak_claims(claims)
        username: str = user_info["username"]
        _oidc_roles: list[str] = user_info["roles"]
    else:
        # Generic OIDC: prefer ``preferred_username``, fall back to ``sub``
        username = (
            claims.get("preferred_username")
            or claims.get("email")
            or claims.get("sub")
            or ""
        )
        _oidc_roles = []

    if not username:
        raise HTTPException(status_code=400, detail="Identity provider did not supply a username")

    # Ensure the user exists locally (JIT provisioning for OIDC users)
    if not auth.is_active(username):
        try:
            from ..auth import UserRepository, _get_user_repository  # noqa: F401
            repo = _get_user_repository()
            if repo.get_user(username) is None:
                import secrets as _sec
                repo._seed_user(username, _sec.token_hex(32), active=True)
                _logger.info("JIT-provisioned OIDC user %r", username)
        except Exception as exc:
            _logger.error("JIT user provisioning failed for %r: %s", username, exc)
            raise HTTPException(status_code=500, detail="User provisioning failed")

    # Assign roles extracted from Keycloak claims (no-op for generic OIDC)
    if _oidc_roles:
        try:
            from ..rbac import add_role as _add_role
            for _role in _oidc_roles:
                _add_role(username, _role)
        except Exception as exc:
            _logger.warning("Role sync for OIDC user %r failed: %s", username, exc)

    # Issue a DocReview360 access JWT
    from datetime import datetime, timedelta, timezone as _tz
    from jose import jwt as _jwt
    import uuid as _uuid
    now = datetime.now(_tz.utc)
    jti = str(_uuid.uuid4())
    expire = now + timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": username,
        "jti": jti,
        "iat": now,
        "exp": expire,
        "iss": auth.TOKEN_ISSUER,
        "aud": auth.TOKEN_AUDIENCE,
        "auth_method": "oidc",
    }
    access_token = _jwt.encode(payload, auth.SECRET_KEY, algorithm=auth.ALGORITHM)

    # Record the session
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    oidc_client.create_user_session(
        username=username,
        jti=jti,
        expires_at=expire,
        auth_method="oidc",
        ip_address=ip,
        user_agent=ua,
    )

    log_event("login", user_id=username, message=f"OIDC login from {ip or 'unknown'}")

    # Set httpOnly cookie and redirect to dashboard
    redirect_resp = RedirectResponse("/projects", status_code=303)
    redirect_resp.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return redirect_resp


# ---------------------------------------------------------------------------
# Session management endpoints
# ---------------------------------------------------------------------------


@router.get("/sessions")
async def list_sessions(
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[dict]:
    """Return all active sessions for the authenticated user."""
    return oidc_client.list_user_sessions(current_user.username)


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, str]:
    """Revoke a specific session by its ``session_id``.

    Only the session owner may revoke their own sessions.
    """
    from sqlalchemy import text as _text
    db = oidc_client._get_db()
    with db.session() as conn:
        row = conn.execute(
            _text("SELECT jti, username FROM user_sessions WHERE id = :sid"),
            {"sid": session_id},
        ).fetchone()
        if row is None or row[1] != current_user.username:
            raise HTTPException(status_code=404, detail="Session not found")
        jti = row[0]
        conn.execute(
            _text("UPDATE user_sessions SET is_active = 0 WHERE id = :sid"),
            {"sid": session_id},
        )
    # Also add jti to the revoked-token table
    from datetime import datetime, timedelta, timezone as _tz
    auth.revoke_token(jti, datetime.now(_tz.utc) + timedelta(days=7))
    return {"detail": "Session revoked"}


# ---------------------------------------------------------------------------
# CAC/PIV smart card authentication
# ---------------------------------------------------------------------------


@router.post("/piv/verify")
async def piv_verify(request: Request, response: Response) -> auth.Token:
    """Authenticate via a CAC/PIV client certificate.

    The reverse proxy (nginx/Apache) must forward the client certificate in
    the ``X-Client-Cert`` (or ``X-SSL-Cert``) header as a PEM-encoded string.
    Set ``DOCREVIEW360_PIV_ENABLED=true`` to activate.
    """
    from .. import piv_cac

    if not piv_cac.piv_enabled():
        raise HTTPException(status_code=404, detail="CAC/PIV authentication is not enabled")

    cert_pem = piv_cac.extract_cert_from_headers(dict(request.headers))
    if not cert_pem:
        raise HTTPException(
            status_code=400,
            detail="No client certificate found in request headers",
        )

    try:
        username, roles = piv_cac.authenticate_piv(cert_pem)
    except ValueError as exc:
        log_event("piv_auth_failure", severity="warning", reason=str(exc))
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    # JIT-provision the user if needed
    repo = auth._get_user_repository()
    if repo.get_user(username) is None:
        import secrets as _sec
        repo._seed_user(username, _sec.token_hex(32), active=True)
        _logger.info("JIT-provisioned PIV user %r", username)

    # Assign roles
    try:
        from .. import rbac as _rbac
        for role in roles:
            _rbac.add_role(username, role)
    except Exception as _role_exc:
        _logger.debug("PIV role assignment failed (non-fatal): %s", _role_exc)

    # Issue JWT
    from datetime import datetime, timedelta, timezone as _tz
    from jose import jwt as _jwt
    import uuid as _uuid

    now = datetime.now(_tz.utc)
    jti = str(_uuid.uuid4())
    expire = now + timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": username,
        "jti": jti,
        "iat": now,
        "exp": expire,
        "iss": auth.TOKEN_ISSUER,
        "aud": auth.TOKEN_AUDIENCE,
        "auth_method": "piv",
    }
    access_token = _jwt.encode(payload, auth.SECRET_KEY, algorithm=auth.ALGORITHM)

    ip = request.client.host if request.client else None
    oidc_client.create_user_session(
        username=username,
        jti=jti,
        expires_at=expire,
        auth_method="piv",
        ip_address=ip,
        user_agent=request.headers.get("user-agent"),
    )
    log_event("login", user_id=username, message=f"PIV/CAC login from {ip or 'unknown'}")

    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return auth.Token(access_token=access_token, token_type="bearer")


# ---------------------------------------------------------------------------
# WebAuthn / FIDO2 endpoints
# ---------------------------------------------------------------------------


@router.post("/webauthn/register/begin")
async def webauthn_register_begin(
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """Begin a WebAuthn credential registration ceremony for the current user."""
    try:
        from .. import webauthn_auth
    except ImportError as exc:
        raise HTTPException(status_code=501, detail="WebAuthn module unavailable") from exc

    if not webauthn_auth.webauthn_enabled():
        raise HTTPException(status_code=404, detail="WebAuthn is not enabled on this server")

    try:
        options_json, challenge_b64 = webauthn_auth.begin_registration(
            current_user.username, current_user.username
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    import json
    return {"options": json.loads(options_json), "challenge": challenge_b64}


@router.post("/webauthn/register/complete")
async def webauthn_register_complete(
    request: Request,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, str]:
    """Complete a WebAuthn registration ceremony and store the credential."""
    try:
        from .. import webauthn_auth
    except ImportError as exc:
        raise HTTPException(status_code=501, detail="WebAuthn module unavailable") from exc

    if not webauthn_auth.webauthn_enabled():
        raise HTTPException(status_code=404, detail="WebAuthn is not enabled on this server")

    body = await request.json()
    credential_response = body.get("credential")
    challenge_b64 = body.get("challenge")
    if not credential_response or not challenge_b64:
        raise HTTPException(status_code=400, detail="credential and challenge are required")

    import json
    try:
        credential_id = webauthn_auth.complete_registration(
            current_user.username,
            json.dumps(credential_response),
            challenge_b64,
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    log_event("webauthn_register", user_id=current_user.username, credential_id=credential_id)
    return {"credential_id": credential_id, "detail": "WebAuthn credential registered"}


@router.post("/webauthn/authenticate/begin")
async def webauthn_auth_begin(request: Request) -> dict:
    """Begin a WebAuthn authentication ceremony."""
    try:
        from .. import webauthn_auth
    except ImportError as exc:
        raise HTTPException(status_code=501, detail="WebAuthn module unavailable") from exc

    if not webauthn_auth.webauthn_enabled():
        raise HTTPException(status_code=404, detail="WebAuthn is not enabled on this server")

    body = await request.json()
    username = body.get("username", "")

    try:
        options_json, challenge_b64 = webauthn_auth.begin_authentication(username)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    import json
    return {"options": json.loads(options_json), "challenge": challenge_b64}


@router.post("/webauthn/authenticate/complete")
async def webauthn_auth_complete(request: Request, response: Response) -> auth.Token:
    """Complete a WebAuthn authentication ceremony and issue a JWT."""
    try:
        from .. import webauthn_auth
    except ImportError as exc:
        raise HTTPException(status_code=501, detail="WebAuthn module unavailable") from exc

    if not webauthn_auth.webauthn_enabled():
        raise HTTPException(status_code=404, detail="WebAuthn is not enabled on this server")

    body = await request.json()
    username = body.get("username", "")
    assertion = body.get("assertion")
    challenge_b64 = body.get("challenge")
    if not assertion or not challenge_b64:
        raise HTTPException(status_code=400, detail="assertion and challenge are required")

    import json
    try:
        ok = webauthn_auth.complete_authentication(username, json.dumps(assertion), challenge_b64)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not ok:
        log_event("webauthn_auth_failure", user_id=username, severity="warning")
        raise HTTPException(status_code=401, detail="WebAuthn authentication failed")

    # Issue JWT
    from datetime import datetime, timedelta, timezone as _tz
    from jose import jwt as _jwt
    import uuid as _uuid

    now = datetime.now(_tz.utc)
    jti = str(_uuid.uuid4())
    expire = now + timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    jwt_payload = {
        "sub": username,
        "jti": jti,
        "iat": now,
        "exp": expire,
        "iss": auth.TOKEN_ISSUER,
        "aud": auth.TOKEN_AUDIENCE,
        "auth_method": "webauthn",
    }
    access_token = _jwt.encode(jwt_payload, auth.SECRET_KEY, algorithm=auth.ALGORITHM)

    ip = request.client.host if request.client else None
    oidc_client.create_user_session(
        username=username,
        jti=jti,
        expires_at=expire,
        auth_method="webauthn",
        ip_address=ip,
        user_agent=request.headers.get("user-agent"),
    )
    log_event("login", user_id=username, message=f"WebAuthn login from {ip or 'unknown'}")

    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return auth.Token(access_token=access_token, token_type="bearer")


@router.get("/webauthn/credentials")
async def webauthn_list_credentials(
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[dict]:
    """List all registered WebAuthn credentials for the current user."""
    try:
        from .. import webauthn_auth
    except ImportError:
        return []
    return webauthn_auth.list_credentials(current_user.username)


@router.delete("/webauthn/credentials/{credential_id}")
async def webauthn_delete_credential(
    credential_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, str]:
    """Remove a registered WebAuthn credential."""
    try:
        from .. import webauthn_auth
    except ImportError as exc:
        raise HTTPException(status_code=501, detail="WebAuthn module unavailable") from exc

    removed = webauthn_auth.delete_credential(credential_id, current_user.username)
    if not removed:
        raise HTTPException(status_code=404, detail="Credential not found")
    log_event("webauthn_credential_deleted", user_id=current_user.username,
              credential_id=credential_id)
    return {"detail": "Credential removed"}

# SPDX-License-Identifier: MIT
"""SAML 2.0 SP routes for DocReview360.

Routes
------
GET  /saml/login     Initiate SAML flow -- redirects the browser to the IdP.
POST /saml/acs       Assertion Consumer Service -- IdP posts here after auth.
GET  /saml/metadata  Return SP metadata XML for registration with the IdP.
POST /saml/sls       Single Logout Service -- handle IdP-initiated logout.
"""

from __future__ import annotations

import logging
import secrets
import uuid
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.responses import Response as _Response

from .. import auth, saml_auth
from ..logs import log_event

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/saml", tags=["saml"])

_SESSION_COOKIE_MAX_AGE: int = auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60


# ---------------------------------------------------------------------------
# Helper: issue a DocReview360 JWT (mirrors oidc_callback pattern)
# ---------------------------------------------------------------------------


def _issue_jwt_and_redirect(
    username: str,
    auth_method: str,
    request: Request,
    redirect_to: str = "/projects",
) -> RedirectResponse:
    """Create a DocReview360 access token and redirect with an httpOnly cookie."""
    from datetime import datetime
    from datetime import timezone as _tz

    from jose import jwt as _jwt

    now = datetime.now(_tz.utc)
    jti = str(uuid.uuid4())
    expire = now + timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": username,
        "jti": jti,
        "iat": now,
        "exp": expire,
        "iss": auth.TOKEN_ISSUER,
        "aud": auth.TOKEN_AUDIENCE,
        "auth_method": auth_method,
    }
    access_token = _jwt.encode(payload, auth.SECRET_KEY, algorithm=auth.ALGORITHM)

    # Record the session (best-effort -- mirrors OIDC callback)
    try:
        from .. import oidc_client

        oidc_client.create_user_session(
            username=username,
            jti=jti,
            expires_at=expire,
            auth_method=auth_method,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except Exception as exc:  # noqa: BLE001
        _logger.warning("Could not record SAML session for %r: %s", username, exc)

    ip = request.client.host if request.client else "unknown"
    log_event("login", user_id=username, message=f"SAML login from {ip}")

    redirect_resp = RedirectResponse(redirect_to, status_code=303)
    redirect_resp.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=_SESSION_COOKIE_MAX_AGE,
    )
    return redirect_resp


def _jit_provision(username: str) -> None:
    """Create a local user record for a SAML-authenticated user if absent."""
    from ..auth import _get_user_repository

    repo = _get_user_repository()
    if repo.get_user(username) is None:
        repo._seed_user(username, secrets.token_hex(32), active=True)
        _logger.info("JIT-provisioned SAML user %r", username)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/login")
async def saml_login(request: Request) -> Any:
    """Initiate a SAML authentication request.

    Redirects the browser to the IdP's Single Sign-On URL.
    """
    if not saml_auth.saml_enabled():
        raise HTTPException(status_code=404, detail="SAML authentication is not enabled")

    try:
        redirect_url, _req_id = saml_auth.build_auth_request()
    except RuntimeError as exc:
        _logger.error("SAML login initiation failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return RedirectResponse(redirect_url, status_code=302)


@router.post("/acs")
async def saml_acs(
    request: Request,
    SAMLResponse: str = Form(...),
) -> Any:
    """Assertion Consumer Service -- process the IdP's SAML response.

    Steps:
    1. Validate the SAML response.
    2. Extract username and roles.
    3. JIT-provision the user if not present.
    4. Issue a DocReview360 JWT cookie and redirect to /projects.
    """
    if not saml_auth.saml_enabled():
        raise HTTPException(status_code=404, detail="SAML authentication is not enabled")

    attributes = saml_auth.process_saml_response(SAMLResponse)
    if attributes is None:
        _logger.warning("SAML ACS: response validation failed")
        raise HTTPException(status_code=401, detail="SAML response validation failed")

    username = saml_auth.extract_username(attributes)
    if not username:
        _logger.warning("SAML ACS: no username found in attributes %s", list(attributes.keys()))
        raise HTTPException(
            status_code=400, detail="Identity provider did not supply a username"
        )

    # JIT-provision if the user does not exist locally
    try:
        _jit_provision(username)
    except Exception as exc:
        _logger.error("JIT user provisioning failed for %r: %s", username, exc)
        raise HTTPException(status_code=500, detail="User provisioning failed") from exc

    # Apply SAML-supplied roles (best-effort -- adds roles, never removes)
    roles = saml_auth.extract_roles(attributes)
    if roles:
        try:
            from .. import rbac as _rbac

            for role in roles:
                _rbac.add_role(username, role)
        except Exception as exc:  # noqa: BLE001
            _logger.warning("Could not assign SAML roles to %r: %s", username, exc)

    return _issue_jwt_and_redirect(username, auth_method="saml", request=request)


@router.get("/metadata")
async def saml_metadata() -> Any:
    """Return the SP metadata XML for registration with the IdP."""
    if not saml_auth.saml_enabled():
        raise HTTPException(status_code=404, detail="SAML authentication is not enabled")

    try:
        xml = saml_auth.get_sp_metadata()
    except RuntimeError as exc:
        _logger.error("SP metadata generation failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return _Response(content=xml, media_type="application/xml")


@router.post("/sls")
async def saml_sls(
    request: Request,
    SAMLRequest: str | None = Form(default=None),
    SAMLResponse: str | None = Form(default=None),
) -> Any:
    """Single Logout Service -- handle IdP-initiated or SP-initiated logout.

    For IdP-initiated SLO the IdP sends a SAMLRequest; for SP-initiated
    SLO the IdP sends a SAMLResponse confirming the logout.

    Currently logs the event and clears the session cookie.  Full SLO
    (token revocation, session invalidation) can be layered on top once
    the IdP integration is configured.
    """
    if not saml_auth.saml_enabled():
        raise HTTPException(status_code=404, detail="SAML authentication is not enabled")

    # Identify the user from the existing session cookie (best-effort)
    cookie_token = request.cookies.get("access_token")
    username = "unknown"
    if cookie_token:
        try:
            from jose import jwt as _jwt

            claims = _jwt.decode(
                cookie_token,
                auth.SECRET_KEY,
                algorithms=[auth.ALGORITHM],
                audience=auth.TOKEN_AUDIENCE,
                issuer=auth.TOKEN_ISSUER,
            )
            username = claims.get("sub", "unknown")
            jti = claims.get("jti")
            if jti:
                from datetime import datetime
                from datetime import timezone as _tz

                auth.revoke_token(jti, datetime.now(_tz.utc))
        except Exception:  # noqa: BLE001 -- token may already be invalid
            pass

    log_event("logout", user_id=username, message="SAML SLO logout")

    redirect_resp = RedirectResponse("/", status_code=303)
    redirect_resp.delete_cookie("access_token")
    return redirect_resp

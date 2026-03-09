"""Auth sub-router: /token, /oidc/token, /me, /logout, /oidc/me, /login, /dashboard, /help, /."""
from __future__ import annotations

import hashlib
import hmac
import logging
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from markdown_it import MarkdownIt

from .. import auth
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

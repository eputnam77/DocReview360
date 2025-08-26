"""Authentication utilities for DocReview360."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel


def _require_env(name: str) -> str:
    """Return the value of ``name`` or raise a ``RuntimeError`` if missing."""

    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} environment variable required")
    return value


SECRET_KEY = _require_env("DOCREVIEW360_SECRET_KEY")
ALGORITHM = _require_env("DOCREVIEW360_ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(_require_env("DOCREVIEW360_ACCESS_EXPIRE_MINUTES"))

# separate secret for the OIDC flow
OIDC_SECRET_KEY = _require_env("DOCREVIEW360_OIDC_SECRET_KEY")
OIDC_ALGORITHM = _require_env("DOCREVIEW360_OIDC_ALGORITHM")
OIDC_TOKEN_EXPIRE_MINUTES = int(_require_env("DOCREVIEW360_OIDC_EXPIRE_MINUTES"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)
oidc_scheme = OAuth2PasswordBearer(tokenUrl="oidc/token", auto_error=False)


class Token(BaseModel):
    """Response model for access tokens."""

    access_token: str
    token_type: str


class User(BaseModel):
    """Simple user model."""

    username: str
    active: bool = True


FAKE_USERS_DB = {
    "alice": {
        "username": "alice",
        "password": "password",
        "otp": "123456",
        "active": True,
    },
    "bob": {
        "username": "bob",
        "password": "password",
        "otp": "123456",
        "active": True,
    },
}


def is_active(username: str) -> bool:
    """Return ``True`` if ``username`` is marked active."""

    entry = FAKE_USERS_DB.get(username)
    return bool(entry and entry.get("active", True))


def authenticate_user(username: str, password: str) -> User | None:
    """Return ``User`` if credentials match and user is active."""

    if not username or not password:
        return None

    user = FAKE_USERS_DB.get(username)
    if user and user.get("password") == password and user.get("active", True):
        return User(username=username, active=True)
    return None


def authenticate_mfa(username: str, password: str, otp: str) -> User | None:
    """Return ``User`` if credentials, OTP match, and user is active."""
    user = FAKE_USERS_DB.get(username)
    if not user:
        return None
    if (
        user.get("password") != password
        or user.get("otp") != otp
        or not user.get("active", True)
    ):
        return None
    return User(username=username, active=True)


def keycloak_mfa_login(username: str, password: str, otp: str) -> str:
    """Return a token from the Keycloak MFA stub."""
    from .stubs.task76 import authenticate_keycloak

    return authenticate_keycloak(username, password, otp)


def create_access_token(data: Dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Return a signed JWT access token."""

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return str(jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM))


def get_current_user(request: Request, token: str | None = Depends(oauth2_scheme)) -> User:
    token = request.cookies.get("access_token") or token
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc
    user = FAKE_USERS_DB.get(username)
    if not user or not user.get("active", True):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    return User(username=username, active=True)


async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
    """Issue a short-lived JWT bearer token."""

    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token({"sub": user.username}, access_token_expires)
    return Token(access_token=access_token, token_type="bearer")


async def login_for_oidc_token(form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
    """Return an ID token for valid credentials using a separate secret."""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    token_expires = timedelta(minutes=OIDC_TOKEN_EXPIRE_MINUTES)
    id_token = create_id_token({"sub": user.username}, token_expires)
    return Token(access_token=id_token, token_type="bearer")


def create_id_token(data: Dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Return an ID token for OIDC authentication."""

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return str(jwt.encode(to_encode, OIDC_SECRET_KEY, algorithm=OIDC_ALGORITHM))


def get_current_user_oidc(request: Request, token: str | None = Depends(oidc_scheme)) -> User:
    """Validate ID token and return the associated user."""
    token = request.cookies.get("access_token") or token
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    try:
        payload = jwt.decode(token, OIDC_SECRET_KEY, algorithms=[OIDC_ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc
    user = FAKE_USERS_DB.get(username)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    return User(username=username)

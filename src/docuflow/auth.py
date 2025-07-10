"""Authentication utilities for DocuFlow."""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel

SECRET_KEY = os.getenv("DOCUFLOW_SECRET_KEY", "secret-key")  # pragma: no cover
ALGORITHM = os.getenv("DOCUFLOW_ALGORITHM", "HS256")  # pragma: no cover
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("DOCUFLOW_ACCESS_EXPIRE_MINUTES", "30")
)  # pragma: no cover

# separate secret for OIDC demonstration
OIDC_SECRET_KEY = os.getenv("DOCUFLOW_OIDC_SECRET_KEY", "oidc-secret")  # pragma: no cover
OIDC_ALGORITHM = os.getenv("DOCUFLOW_OIDC_ALGORITHM", "HS256")  # pragma: no cover
OIDC_TOKEN_EXPIRE_MINUTES = int(os.getenv("DOCUFLOW_OIDC_EXPIRE_MINUTES", "30"))  # pragma: no cover

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
oidc_scheme = OAuth2PasswordBearer(tokenUrl="oidc/token")


class Token(BaseModel):
    """Response model for access tokens."""

    access_token: str
    token_type: str


class User(BaseModel):
    """Simple user model."""

    username: str


FAKE_USERS_DB = {"alice": {"username": "alice", "password": "password", "otp": "123456"}}


def authenticate_user(username: str, password: str) -> User | None:
    """Return ``User`` if credentials match, otherwise ``None``."""

    if not username or not password:
        return None

    user = FAKE_USERS_DB.get(username)
    if user and user["password"] == password:
        return User(username=username)
    return None


def authenticate_mfa(username: str, password: str, otp: str) -> User | None:
    """Return ``User`` if credentials and OTP match."""
    user = FAKE_USERS_DB.get(username)
    if not user:
        return None
    if user.get("password") != password or user.get("otp") != otp:
        return None
    return User(username=username)


def keycloak_mfa_login(username: str, password: str, otp: str) -> str:
    """Return a token from the Keycloak MFA stub."""
    from .stubs.task76 import authenticate_keycloak

    return authenticate_keycloak(username, password, otp)


def create_access_token(data: Dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Return a signed JWT access token."""

    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return str(jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM))


def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
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
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    return User(username=username)


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
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return str(jwt.encode(to_encode, OIDC_SECRET_KEY, algorithm=OIDC_ALGORITHM))


def get_current_user_oidc(token: str = Depends(oidc_scheme)) -> User:
    """Validate ID token and return the associated user."""
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

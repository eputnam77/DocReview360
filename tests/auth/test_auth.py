"""Authentication regression tests for issuer/audience claims and CSRF."""

from __future__ import annotations

import importlib
from datetime import datetime, timedelta, timezone
from typing import Callable

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from jose import jwt

import docreview360.auth as auth


@pytest.fixture
def fresh_auth() -> auth:
    """Reload the auth module so environment overrides take effect."""

    module = importlib.reload(auth)
    return module


def _client_for_dependency(dep: Callable[..., auth.User]) -> TestClient:
    app = FastAPI()

    @app.get("/me")
    def read_me(user: auth.User = Depends(dep)) -> dict[str, str]:
        return {"username": user.username}

    return TestClient(app)


@pytest.mark.parametrize("claim", ["iss", "aud"])
def test_access_token_rejects_claim_mismatch(fresh_auth: auth, claim: str) -> None:
    client = _client_for_dependency(fresh_auth.get_current_user)
    valid_token = fresh_auth.create_access_token({"sub": "alice"}, timedelta(minutes=5))

    payload = {
        "sub": "alice",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        "iss": fresh_auth.TOKEN_ISSUER,
        "aud": fresh_auth.TOKEN_AUDIENCE,
    }
    payload[claim] = f"unexpected-{claim}"
    tampered = jwt.encode(
        payload,
        fresh_auth.SECRET_KEY,
        algorithm=fresh_auth.ALGORITHM,
    )

    mismatch_response = client.get(
        "/me",
        headers={"Authorization": f"Bearer {tampered}"},
    )
    assert mismatch_response.status_code == 401

    ok_response = client.get(
        "/me",
        headers={"Authorization": f"Bearer {valid_token}"},
    )
    assert ok_response.status_code == 200
    assert ok_response.json() == {"username": "alice"}


@pytest.mark.parametrize("claim", ["iss", "aud"])
def test_oidc_token_rejects_claim_mismatch(fresh_auth: auth, claim: str) -> None:
    client = _client_for_dependency(fresh_auth.get_current_user_oidc)
    valid_token = fresh_auth.create_id_token({"sub": "alice"}, timedelta(minutes=5))

    payload = {
        "sub": "alice",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        "iss": fresh_auth.OIDC_TOKEN_ISSUER,
        "aud": fresh_auth.OIDC_TOKEN_AUDIENCE,
    }
    payload[claim] = f"unexpected-{claim}"
    tampered = jwt.encode(
        payload,
        fresh_auth.OIDC_SECRET_KEY,
        algorithm=fresh_auth.OIDC_ALGORITHM,
    )

    mismatch_response = client.get(
        "/me",
        headers={"Authorization": f"Bearer {tampered}"},
    )
    assert mismatch_response.status_code == 401

    ok_response = client.get(
        "/me",
        headers={"Authorization": f"Bearer {valid_token}"},
    )
    assert ok_response.status_code == 200
    assert ok_response.json() == {"username": "alice"}


def test_cookie_auth_requires_csrf_header(fresh_auth: auth) -> None:
    client = _client_for_dependency(fresh_auth.get_current_user)
    token = fresh_auth.create_access_token({"sub": "alice"}, timedelta(minutes=5))

    client.cookies.set("access_token", token)
    missing_header = client.get("/me")
    assert missing_header.status_code == 403
    client.cookies.clear()

    client.cookies.set("access_token", token)
    client.cookies.set("csrf_token", "expected")
    mismatch_header = client.get("/me", headers={"X-CSRF-Token": "other"})
    assert mismatch_header.status_code == 403
    client.cookies.clear()

    client.cookies.set("access_token", token)
    client.cookies.set("csrf_token", "expected")
    ok_response = client.get("/me", headers={"X-CSRF-Token": "expected"})
    assert ok_response.status_code == 200
    assert ok_response.json() == {"username": "alice"}

from __future__ import annotations

from uuid import uuid4

from docreview360 import auth
from docreview360.api import app
from fastapi.testclient import TestClient

TEST_PASSWORD = "Password123!"


def test_jwt_token_flow() -> None:
    client = TestClient(app)
    username = f"alice-token-{uuid4().hex}"
    auth.USER_REPOSITORY.create_user(username, TEST_PASSWORD)
    resp = client.post("/token", data={"username": username, "password": TEST_PASSWORD})
    assert resp.status_code == 200
    payload = resp.json()
    token = payload["access_token"]
    assert payload["token_type"] == "bearer"
    assert payload["expires_in"] == auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    assert payload["refresh_token"]

    protected = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert protected.status_code == 200
    assert protected.json()["username"] == username


def test_token_accepts_json_body() -> None:
    client = TestClient(app)
    username = f"json-login-{uuid4().hex}"
    auth.USER_REPOSITORY.create_user(username, TEST_PASSWORD)

    resp = client.post(
        "/token",
        json={"username": username, "password": TEST_PASSWORD},
    )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["access_token"]
    assert payload["refresh_token"]
    assert payload["expires_in"] == auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60


def test_refresh_token_rotates_and_reuse_revokes_family() -> None:
    client = TestClient(app)
    username = f"refresh-login-{uuid4().hex}"
    auth.USER_REPOSITORY.create_user(username, TEST_PASSWORD)

    login_resp = client.post("/token", json={"username": username, "password": TEST_PASSWORD})
    assert login_resp.status_code == 200
    first_payload = login_resp.json()

    refresh_resp = client.post(
        "/token/refresh",
        json={"refresh_token": first_payload["refresh_token"]},
    )
    assert refresh_resp.status_code == 200
    refreshed_payload = refresh_resp.json()
    assert refreshed_payload["access_token"] != first_payload["access_token"]
    assert refreshed_payload["refresh_token"] != first_payload["refresh_token"]
    assert refreshed_payload["expires_in"] == auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    reuse_resp = client.post(
        "/token/refresh",
        json={"refresh_token": first_payload["refresh_token"]},
    )
    assert reuse_resp.status_code == 401
    body = reuse_resp.json()
    detail_text = (body.get("detail") or body.get("message") or "").lower()
    assert "reuse" in detail_text

    protected = client.get(
        "/me",
        headers={"Authorization": f"Bearer {refreshed_payload['access_token']}"},
    )
    assert protected.status_code == 401


def test_login_invalid_credentials() -> None:
    client = TestClient(app)
    resp = client.post("/token", data={"username": "alice", "password": "bad"})
    assert resp.status_code == 401


def test_protected_invalid_token() -> None:
    client = TestClient(app)
    resp = client.get("/me", headers={"Authorization": "Bearer bad"})
    assert resp.status_code == 401


def test_oidc_flow() -> None:
    client = TestClient(app)
    username = f"oidc-user-{uuid4().hex}"
    auth.USER_REPOSITORY.create_user(username, TEST_PASSWORD)
    resp = client.post("/oidc/token", data={"username": username, "password": TEST_PASSWORD})
    assert resp.status_code == 200
    payload = resp.json()
    token = payload["access_token"]
    assert payload["expires_in"] == auth.OIDC_TOKEN_EXPIRE_MINUTES * 60
    assert payload["refresh_token"] is None
    user_resp = client.get("/oidc/me", headers={"Authorization": f"Bearer {token}"})
    assert user_resp.status_code == 200
    assert user_resp.json()["username"] == username

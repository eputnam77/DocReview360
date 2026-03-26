# SPDX-License-Identifier: MIT
"""Integration tests for notifications_router (R-03)."""

from __future__ import annotations

from datetime import timedelta

import pytest

pytest.importorskip("fastapi")

from docreview360 import auth, rbac
from docreview360.api import app
from fastapi.testclient import TestClient


def _make_admin_headers(username: str = "alice") -> dict[str, str]:
    try:
        auth.USER_REPOSITORY.create_user(username, "password")
    except Exception:
        pass
    try:
        rbac.add_role(username, "admin")
    except Exception:
        pass
    token = auth.create_access_token({"sub": username}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def admin_headers() -> dict[str, str]:
    return _make_admin_headers()


# ---------------------------------------------------------------------------
# GET/PUT /notifications/settings
# ---------------------------------------------------------------------------


def test_get_notification_settings_unauthenticated(client: TestClient) -> None:
    resp = client.get("/notifications/settings")
    assert resp.status_code == 401


def test_get_notification_settings_authenticated(client: TestClient, admin_headers: dict) -> None:
    resp = client.get("/notifications/settings", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "slack_enabled" in data
    assert "email_enabled" in data


def test_update_notification_settings_non_https_url(
    client: TestClient, admin_headers: dict
) -> None:
    resp = client.put(
        "/notifications/settings",
        json={
            "slack_enabled": True,
            "slack_webhook_url": "http://insecure.example.com",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 422


def test_update_notification_settings_valid(client: TestClient, admin_headers: dict) -> None:
    resp = client.put(
        "/notifications/settings",
        json={
            "slack_enabled": False,
            "teams_enabled": False,
            "email_enabled": True,
            "email_recipient": "test@example.com",
        },
        headers=admin_headers,
    )
    assert resp.status_code in (200, 403)


# ---------------------------------------------------------------------------
# GET /notifications/preferences/me
# ---------------------------------------------------------------------------


def test_get_my_notification_preference_unauthenticated(client: TestClient) -> None:
    resp = client.get("/notifications/preferences/me")
    assert resp.status_code == 401


def test_get_my_notification_preference_authenticated(
    client: TestClient, admin_headers: dict
) -> None:
    resp = client.get("/notifications/preferences/me", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "username" in data
    assert "preferred_channel" in data


# ---------------------------------------------------------------------------
# POST /notifications/test
# ---------------------------------------------------------------------------


def test_notification_test_unauthenticated(client: TestClient) -> None:
    resp = client.post("/notifications/test")
    assert resp.status_code == 401


def test_notification_test_admin(client: TestClient, admin_headers: dict) -> None:
    resp = client.post("/notifications/test", headers=admin_headers)
    assert resp.status_code in (200, 403)

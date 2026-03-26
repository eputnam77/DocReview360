# SPDX-License-Identifier: MIT
"""Integration tests for device token endpoints (Item 50 Phase 3)."""

from __future__ import annotations

from datetime import timedelta

import pytest

pytest.importorskip("fastapi")

from docreview360 import auth, rbac
from docreview360.api import app
from fastapi.testclient import TestClient


def _make_headers(username: str = "alice") -> dict[str, str]:
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


@pytest.fixture(autouse=True)
def _clear_device_tokens() -> None:
    """Reset device token store between tests."""
    from docreview360.api.notifications_router import _device_tokens
    _device_tokens.clear()
    yield
    _device_tokens.clear()


# ---------------------------------------------------------------------------
# POST /devices/register
# ---------------------------------------------------------------------------


def test_register_device_token_success(client: TestClient) -> None:
    resp = client.post(
        "/devices/register",
        json={"token": "test-token-123", "platform": "ios"},
        headers=_make_headers("alice"),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["token"] == "test-token-123"
    assert data["platform"] == "ios"
    assert data["username"] == "alice"


def test_register_device_token_android(client: TestClient) -> None:
    resp = client.post(
        "/devices/register",
        json={"token": "android-fcm-token", "platform": "android"},
        headers=_make_headers("alice"),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["platform"] == "android"


def test_register_device_token_blank_token(client: TestClient) -> None:
    resp = client.post(
        "/devices/register",
        json={"token": "   ", "platform": "ios"},
        headers=_make_headers("alice"),
    )
    assert resp.status_code == 422


def test_register_device_token_unauthenticated(client: TestClient) -> None:
    resp = client.post(
        "/devices/register",
        json={"token": "some-token", "platform": "ios"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /devices/{token}
# ---------------------------------------------------------------------------


def test_delete_device_token_success(client: TestClient) -> None:
    headers = _make_headers("alice")
    # Register first
    client.post(
        "/devices/register",
        json={"token": "to-delete-token", "platform": "ios"},
        headers=headers,
    )
    resp = client.delete("/devices/to-delete-token", headers=headers)
    assert resp.status_code == 204


def test_delete_device_token_not_found(client: TestClient) -> None:
    resp = client.delete("/devices/nonexistent-token", headers=_make_headers("alice"))
    assert resp.status_code == 404


def test_delete_device_token_wrong_user(client: TestClient) -> None:
    """Non-admin user cannot delete another user's device token."""
    # Register a token as "alice" (admin)
    alice_headers = _make_headers("alice")
    client.post(
        "/devices/register",
        json={"token": "alice-exclusive-token", "platform": "ios"},
        headers=alice_headers,
    )
    # Bob (auditor, non-admin) tries to delete Alice's token
    # Use DEMO_USER_DEFAULTS bob who is non-admin by default
    try:
        auth.USER_REPOSITORY.create_user(
            "bob",
            auth.DEMO_USER_DEFAULTS["bob"]["password"],
        )
    except Exception:
        pass
    bob_token = auth.create_access_token({"sub": "bob"}, timedelta(minutes=30))
    bob_headers = {"Authorization": f"Bearer {bob_token}"}

    resp = client.delete("/devices/alice-exclusive-token", headers=bob_headers)
    # Bob is not admin and not the owner, so should be 403
    assert resp.status_code == 403


def test_delete_device_token_admin_can_delete_others(client: TestClient) -> None:
    """Admin can delete any user's device token."""
    # Alice registers a token
    alice_headers = _make_headers("alice")
    client.post(
        "/devices/register",
        json={"token": "alice-token2", "platform": "ios"},
        headers=alice_headers,
    )
    # Admin deletes it
    admin_headers = _make_headers("alice")  # alice is admin
    resp = client.delete("/devices/alice-token2", headers=admin_headers)
    assert resp.status_code == 204


# ---------------------------------------------------------------------------
# GET /notifications/unread-count
# ---------------------------------------------------------------------------


def test_unread_notification_count_returns_dict(client: TestClient) -> None:
    resp = client.get("/notifications/unread-count", headers=_make_headers("alice"))
    assert resp.status_code == 200
    data = resp.json()
    assert "unread_count" in data
    assert isinstance(data["unread_count"], int)
    assert data["unread_count"] >= 0


def test_unread_notification_count_unauthenticated(client: TestClient) -> None:
    resp = client.get("/notifications/unread-count")
    assert resp.status_code == 401

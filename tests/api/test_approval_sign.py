# SPDX-License-Identifier: MIT
"""Tests for POST /approvals/{approval_id}/sign endpoint (RELEASE_CHECKLIST §51)."""
from __future__ import annotations

import os
from datetime import timedelta

import pytest

pytest.importorskip("fastapi")

from docreview360 import auth, rbac
from docreview360.api import app
from docreview360.approvals import (
    ApprovalModel,
    approvals,
    create_approval,
    reset_approvals,
)
from docreview360.documents import documents
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_headers(username: str) -> dict[str, str]:
    try:
        auth.USER_REPOSITORY.create_user(
            username,
            "password",
            otp_secret=None,
        )
    except Exception:
        pass
    token = auth.create_access_token({"sub": username}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


def _alice_headers() -> dict[str, str]:
    try:
        auth.USER_REPOSITORY.create_user(
            "alice",
            auth.DEMO_USER_DEFAULTS["alice"]["password"],
            otp_secret=auth.DEMO_USER_DEFAULTS["alice"].get("otp_secret"),
        )
    except Exception:
        pass
    rbac.add_role("alice", "admin")
    token = auth.create_access_token({"sub": "alice"}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _reset_state():
    """Clean up in-memory state between tests."""
    reset_approvals()
    documents.clear()
    yield
    reset_approvals()
    documents.clear()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def doc_id(client: TestClient) -> str:
    """Create and return a document ID for use in approval tests."""
    resp = client.post(
        "/documents/import",
        files={"file": ("test.md", b"# Test Document\nContent here.", "text/markdown")},
        headers=_alice_headers(),
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_sign_approval_in_app_sandbox(client: TestClient, doc_id: str, monkeypatch):
    """In sandbox mode, signing records an in-app signature immediately."""
    monkeypatch.setenv("SIGNATURE_PROVIDER", "sandbox")

    appr = create_approval("wf-sign-test", "alice", doc_id)
    assert appr.state == "pending"

    resp = client.post(
        f"/approvals/{appr.id}/sign",
        headers=_alice_headers(),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["state"] == "approved"
    assert data["id"] == appr.id
    # In-app signature id should contain the username
    assert "alice" in (data.get("signature") or data.get("signature_id") or "")


def test_sign_approval_already_approved_returns_409(
    client: TestClient, doc_id: str, monkeypatch
):
    """Attempting to sign an already-approved approval returns HTTP 409."""
    monkeypatch.setenv("SIGNATURE_PROVIDER", "sandbox")

    appr = create_approval("wf-sign-409", "alice", doc_id)
    # First sign should succeed
    resp = client.post(f"/approvals/{appr.id}/sign", headers=_alice_headers())
    assert resp.status_code == 200

    # Second sign attempt on same approval should fail
    resp2 = client.post(f"/approvals/{appr.id}/sign", headers=_alice_headers())
    assert resp2.status_code == 409


def test_sign_approval_wrong_user_returns_403(
    client: TestClient, doc_id: str, monkeypatch
):
    """A user who is not the assigned approver gets HTTP 403."""
    monkeypatch.setenv("SIGNATURE_PROVIDER", "sandbox")

    # Approval assigned to 'alice', but 'bob' tries to sign it
    appr = create_approval("wf-sign-403", "alice", doc_id)
    bob_headers = _make_headers("bob")

    resp = client.post(f"/approvals/{appr.id}/sign", headers=bob_headers)
    assert resp.status_code == 403
    assert "not the assigned approver" in resp.json()["detail"].lower()


def test_sign_approval_not_found_returns_404(client: TestClient, monkeypatch):
    """Signing a non-existent approval returns HTTP 404."""
    monkeypatch.setenv("SIGNATURE_PROVIDER", "sandbox")

    resp = client.post(
        "/approvals/nonexistent-id/sign",
        headers=_alice_headers(),
    )
    assert resp.status_code == 404


def test_sign_approval_unauthenticated_returns_401(client: TestClient, doc_id: str):
    """Calling the endpoint without a token returns HTTP 401 or 403."""
    appr = create_approval("wf-sign-noauth", "alice", doc_id)
    resp = client.post(f"/approvals/{appr.id}/sign")
    assert resp.status_code in (401, 403)


def test_sign_approval_none_provider_uses_inapp(
    client: TestClient, doc_id: str, monkeypatch
):
    """SIGNATURE_PROVIDER=none should also use in-app signing."""
    monkeypatch.setenv("SIGNATURE_PROVIDER", "none")

    appr = create_approval("wf-sign-none", "alice", doc_id)
    resp = client.post(f"/approvals/{appr.id}/sign", headers=_alice_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data["state"] == "approved"


def test_sign_approval_response_is_approval_model(
    client: TestClient, doc_id: str, monkeypatch
):
    """The endpoint returns a full ApprovalModel record (not just id/url)."""
    monkeypatch.setenv("SIGNATURE_PROVIDER", "sandbox")

    appr = create_approval("wf-sign-model", "alice", doc_id)
    resp = client.post(f"/approvals/{appr.id}/sign", headers=_alice_headers())
    assert resp.status_code == 200

    data = resp.json()
    # Verify shape — these fields must be present in ApprovalModel
    assert "id" in data
    assert "state" in data
    assert "reviewer" in data
    assert "workflow" in data
    assert data["reviewer"] == "alice"
    assert data["state"] == "approved"

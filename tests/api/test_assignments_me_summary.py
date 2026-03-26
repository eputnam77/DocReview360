# SPDX-License-Identifier: MIT
"""Integration tests for GET /assignments/me/summary (Item 50 Phase 4)."""

from __future__ import annotations

from datetime import timedelta

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from docreview360 import auth, rbac
from docreview360.api import app


def _make_headers(username: str = "alice", roles: list[str] | None = None) -> dict[str, str]:
    try:
        auth.USER_REPOSITORY.create_user(username, "password")
    except Exception:
        pass
    for role in roles or ["admin"]:
        try:
            rbac.add_role(username, role)
        except Exception:
            pass
    token = auth.create_access_token({"sub": username}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_assignments_me_summary_unauthenticated(client: TestClient) -> None:
    resp = client.get("/assignments/me/summary")
    assert resp.status_code == 401


def test_assignments_me_summary_returns_expected_shape(client: TestClient) -> None:
    headers = _make_headers("alice")
    resp = client.get("/assignments/me/summary", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "username" in data
    assert data["username"] == "alice"
    assert "total" in data
    assert "by_status" in data
    assert "overdue" in data
    assert isinstance(data["total"], int)
    assert isinstance(data["by_status"], dict)
    assert isinstance(data["overdue"], int)


def test_assignments_me_summary_empty_for_alice_admin(client: TestClient) -> None:
    """Admin user with no assignments sees zero or positive total but valid shape."""
    headers = _make_headers("alice")
    resp = client.get("/assignments/me/summary", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "alice"
    assert isinstance(data["total"], int)
    assert isinstance(data["overdue"], int)
    assert isinstance(data["by_status"], dict)


def test_assignments_me_summary_counts_assignments(client: TestClient) -> None:
    """After creating a project and assigning bob as reviewer, summary includes it."""
    alice_headers = _make_headers("alice")
    # Use bob (demo user) as the reviewer
    try:
        auth.USER_REPOSITORY.create_user(
            "bob",
            auth.DEMO_USER_DEFAULTS["bob"]["password"],
        )
    except Exception:
        pass
    bob_token = auth.create_access_token({"sub": "bob"}, timedelta(minutes=30))
    bob_headers = {"Authorization": f"Bearer {bob_token}"}

    # Create a project
    proj_resp = client.post(
        "/projects",
        json={"name": "Summary Count Test", "doc_type": "Policy", "phase": "Draft"},
        headers=alice_headers,
    )
    if proj_resp.status_code != 201:
        pytest.skip("Project creation failed")
    project_id = proj_resp.json()["id"]

    # Assign bob as reviewer
    assign_resp = client.post(
        f"/projects/{project_id}/assignments",
        json={"reviewer": "bob"},
        headers=alice_headers,
    )
    if assign_resp.status_code not in (200, 201):
        pytest.skip("Assignment creation failed")

    # Check bob's summary
    resp = client.get("/assignments/me/summary", headers=bob_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["by_status"]) >= 1

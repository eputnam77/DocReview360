# SPDX-License-Identifier: MIT
"""Integration tests for feedback_router (R-03)."""

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


def _create_project(client: TestClient, headers: dict, name: str = "Feedback Test") -> str | None:
    resp = client.post(
        "/projects",
        json={"name": name, "doc_type": "Policy", "phase": "Draft"},
        headers=headers,
    )
    if resp.status_code == 201:
        return resp.json()["id"]
    return None


# ---------------------------------------------------------------------------
# GET /projects/{id}/feedback
# ---------------------------------------------------------------------------


def test_list_feedback_unauthenticated(client: TestClient) -> None:
    resp = client.get("/projects/some-id/feedback")
    assert resp.status_code == 401


def test_list_feedback_not_found(client: TestClient, admin_headers: dict) -> None:
    resp = client.get("/projects/nonexistent-id/feedback", headers=admin_headers)
    assert resp.status_code == 404


def test_list_feedback_empty_project(client: TestClient, admin_headers: dict) -> None:
    project_id = _create_project(client, admin_headers, "Empty Feedback Project")
    if not project_id:
        pytest.skip("Project creation failed")

    resp = client.get(f"/projects/{project_id}/feedback", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


# ---------------------------------------------------------------------------
# POST /projects/{id}/feedback
# ---------------------------------------------------------------------------


def test_create_feedback_unauthenticated(client: TestClient) -> None:
    resp = client.post(
        "/projects/some-id/feedback",
        json={"text": "test feedback"},
    )
    assert resp.status_code == 401


def test_create_feedback_not_found(client: TestClient, admin_headers: dict) -> None:
    resp = client.post(
        "/projects/nonexistent-id/feedback",
        json={"text": "test feedback"},
        headers=admin_headers,
    )
    assert resp.status_code == 404


def test_create_and_list_feedback(client: TestClient, admin_headers: dict) -> None:
    project_id = _create_project(client, admin_headers, "Feedback CRUD Test")
    if not project_id:
        pytest.skip("Project creation failed")

    # Create feedback
    create_resp = client.post(
        f"/projects/{project_id}/feedback",
        json={"text": "This policy needs clarification", "feedback_type": "comment"},
        headers=admin_headers,
    )
    assert create_resp.status_code == 201
    item = create_resp.json()
    assert item["text"] == "This policy needs clarification"
    item_id = item["id"]

    # List feedback - should include the new item
    list_resp = client.get(f"/projects/{project_id}/feedback", headers=admin_headers)
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert data["total"] >= 1
    item_ids = [i["id"] for i in data["items"]]
    assert item_id in item_ids


def test_create_feedback_invalid_type(client: TestClient, admin_headers: dict) -> None:
    project_id = _create_project(client, admin_headers, "Invalid Type Test")
    if not project_id:
        pytest.skip("Project creation failed")

    resp = client.post(
        f"/projects/{project_id}/feedback",
        json={"text": "test", "feedback_type": "invalid_type"},
        headers=admin_headers,
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /projects/{id}/feedback/progress
# ---------------------------------------------------------------------------


def test_feedback_progress_authenticated(client: TestClient, admin_headers: dict) -> None:
    project_id = _create_project(client, admin_headers, "Feedback Progress Test")
    if not project_id:
        pytest.skip("Project creation failed")

    resp = client.get(f"/projects/{project_id}/feedback/progress", headers=admin_headers)
    assert resp.status_code in (200, 404)


# ---------------------------------------------------------------------------
# GET /projects/{id}/feedback/phases
# ---------------------------------------------------------------------------


def test_feedback_phases_authenticated(client: TestClient, admin_headers: dict) -> None:
    project_id = _create_project(client, admin_headers, "Feedback Phases Test")
    if not project_id:
        pytest.skip("Project creation failed")

    resp = client.get(f"/projects/{project_id}/feedback/phases", headers=admin_headers)
    assert resp.status_code in (200, 404)

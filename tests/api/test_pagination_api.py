# SPDX-License-Identifier: MIT
"""Integration tests for pagination on list endpoints (Item 50 Phase 2)."""

from __future__ import annotations

from datetime import timedelta

import pytest

pytest.importorskip("fastapi")

from docreview360 import auth, rbac
from docreview360.api import app
from fastapi.testclient import TestClient


def _make_headers(username: str = "alice", roles: list[str] | None = None) -> dict[str, str]:
    try:
        auth.USER_REPOSITORY.create_user(username, "password")
    except Exception:
        pass
    for role in roles or ["admin", "manager"]:
        try:
            rbac.add_role(username, role)
        except Exception:
            pass
    token = auth.create_access_token({"sub": username}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def alice_headers() -> dict[str, str]:
    return _make_headers("alice")


# ---------------------------------------------------------------------------
# GET /projects
# ---------------------------------------------------------------------------


def test_list_projects_default_pagination(client: TestClient, alice_headers: dict) -> None:
    resp = client.get("/projects", headers=alice_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "skip" in data
    assert "limit" in data
    assert data["skip"] == 0
    assert data["limit"] == 20


def test_list_projects_custom_pagination(client: TestClient, alice_headers: dict) -> None:
    resp = client.get("/projects?skip=0&limit=5", headers=alice_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["limit"] == 5
    assert len(data["items"]) <= 5


def test_list_projects_unauthenticated(client: TestClient) -> None:
    resp = client.get("/projects")
    assert resp.status_code == 401


def test_list_projects_invalid_limit(client: TestClient, alice_headers: dict) -> None:
    resp = client.get("/projects?limit=0", headers=alice_headers)
    assert resp.status_code == 422


def test_list_projects_invalid_skip(client: TestClient, alice_headers: dict) -> None:
    resp = client.get("/projects?skip=-1", headers=alice_headers)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /documents
# ---------------------------------------------------------------------------


def test_list_documents_default_pagination(client: TestClient, alice_headers: dict) -> None:
    resp = client.get("/documents", headers=alice_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["skip"] == 0
    assert data["limit"] == 20


def test_list_documents_custom_pagination(client: TestClient, alice_headers: dict) -> None:
    resp = client.get("/documents?skip=0&limit=10", headers=alice_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["limit"] == 10


def test_list_documents_unauthenticated(client: TestClient) -> None:
    resp = client.get("/documents")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /projects/{id}/feedback
# ---------------------------------------------------------------------------


def test_list_feedback_default_pagination(client: TestClient, alice_headers: dict) -> None:
    # Create a project first
    proj_resp = client.post(
        "/projects",
        json={"name": "Pagination Test", "doc_type": "Policy", "phase": "Draft"},
        headers=alice_headers,
    )
    if proj_resp.status_code != 201:
        pytest.skip("Project creation failed")
    project_id = proj_resp.json()["id"]

    resp = client.get(f"/projects/{project_id}/feedback", headers=alice_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["skip"] == 0
    assert data["limit"] == 20


def test_list_feedback_custom_pagination(client: TestClient, alice_headers: dict) -> None:
    proj_resp = client.post(
        "/projects",
        json={"name": "Pagination Test 2", "doc_type": "Policy", "phase": "Draft"},
        headers=alice_headers,
    )
    if proj_resp.status_code != 201:
        pytest.skip("Project creation failed")
    project_id = proj_resp.json()["id"]

    resp = client.get(f"/projects/{project_id}/feedback?skip=0&limit=5", headers=alice_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["limit"] == 5


def test_list_feedback_not_found(client: TestClient, alice_headers: dict) -> None:
    resp = client.get("/projects/nonexistent-project/feedback", headers=alice_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /projects/{id}/assignments
# ---------------------------------------------------------------------------


def test_list_assignments_default_pagination(client: TestClient, alice_headers: dict) -> None:
    proj_resp = client.post(
        "/projects",
        json={"name": "Assignment Pagination Test", "doc_type": "Policy", "phase": "Draft"},
        headers=alice_headers,
    )
    if proj_resp.status_code != 201:
        pytest.skip("Project creation failed")
    project_id = proj_resp.json()["id"]

    resp = client.get(f"/projects/{project_id}/assignments", headers=alice_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["skip"] == 0
    assert data["limit"] == 20


def test_list_assignments_custom_pagination(client: TestClient, alice_headers: dict) -> None:
    proj_resp = client.post(
        "/projects",
        json={"name": "Assignment Pagination Test 2", "doc_type": "Policy", "phase": "Draft"},
        headers=alice_headers,
    )
    if proj_resp.status_code != 201:
        pytest.skip("Project creation failed")
    project_id = proj_resp.json()["id"]

    resp = client.get(
        f"/projects/{project_id}/assignments?skip=0&limit=5", headers=alice_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["limit"] == 5


# ---------------------------------------------------------------------------
# GET /comments/{project_id}
# ---------------------------------------------------------------------------


def test_list_comments_default_pagination(client: TestClient, alice_headers: dict) -> None:
    proj_resp = client.post(
        "/projects",
        json={"name": "Comment Pagination Test", "doc_type": "Policy", "phase": "Draft"},
        headers=alice_headers,
    )
    if proj_resp.status_code != 201:
        pytest.skip("Project creation failed")
    project_id = proj_resp.json()["id"]

    resp = client.get(f"/comments/{project_id}", headers=alice_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["skip"] == 0
    assert data["limit"] == 20


def test_list_comments_project_not_found(client: TestClient, alice_headers: dict) -> None:
    resp = client.get("/comments/nonexistent-project", headers=alice_headers)
    assert resp.status_code == 404


def test_list_comments_custom_limit(client: TestClient, alice_headers: dict) -> None:
    proj_resp = client.post(
        "/projects",
        json={"name": "Comment Pagination Test 2", "doc_type": "Policy", "phase": "Draft"},
        headers=alice_headers,
    )
    if proj_resp.status_code != 201:
        pytest.skip("Project creation failed")
    project_id = proj_resp.json()["id"]

    resp = client.get(f"/comments/{project_id}?limit=5", headers=alice_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["limit"] == 5


# ---------------------------------------------------------------------------
# GET /projects/{id}/notification-log
# ---------------------------------------------------------------------------


def test_notification_log_default_pagination(client: TestClient, alice_headers: dict) -> None:
    proj_resp = client.post(
        "/projects",
        json={"name": "Notification Pagination Test", "doc_type": "Policy", "phase": "Draft"},
        headers=alice_headers,
    )
    if proj_resp.status_code != 201:
        pytest.skip("Project creation failed")
    project_id = proj_resp.json()["id"]

    resp = client.get(f"/projects/{project_id}/notification-log", headers=alice_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "skip" in data
    assert "limit" in data

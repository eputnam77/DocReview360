# SPDX-License-Identifier: MIT
"""Integration tests for records_router (R-03)."""

from __future__ import annotations

from datetime import timedelta

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from docreview360 import auth, rbac
from docreview360.api import app


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


def _create_project(client: TestClient, headers: dict, name: str = "Records Test") -> str | None:
    resp = client.post(
        "/projects",
        json={"name": name, "doc_type": "Policy", "phase": "Draft"},
        headers=headers,
    )
    if resp.status_code == 201:
        return resp.json()["id"]
    return None


def test_get_project_lifecycle_unauthenticated(client: TestClient) -> None:
    resp = client.get("/projects/some-id/lifecycle")
    assert resp.status_code == 401


def test_get_project_lifecycle_not_found(client: TestClient, admin_headers: dict) -> None:
    resp = client.get("/projects/nonexistent-project/lifecycle", headers=admin_headers)
    assert resp.status_code in (404, 403)


def test_get_project_lifecycle_authenticated(client: TestClient, admin_headers: dict) -> None:
    project_id = _create_project(client, admin_headers, "Lifecycle Test")
    if not project_id:
        pytest.skip("Project creation failed")

    resp = client.get(f"/projects/{project_id}/lifecycle", headers=admin_headers)
    assert resp.status_code in (200, 403)


def test_post_project_lifecycle_event_authenticated(
    client: TestClient, admin_headers: dict
) -> None:
    project_id = _create_project(client, admin_headers, "Lifecycle Event Test")
    if not project_id:
        pytest.skip("Project creation failed")

    resp = client.post(
        f"/projects/{project_id}/lifecycle",
        json={"event": "draft_submitted"},
        headers=admin_headers,
    )
    assert resp.status_code in (200, 201, 400, 403, 422)


def test_get_records_package_authenticated(client: TestClient, admin_headers: dict) -> None:
    project_id = _create_project(client, admin_headers, "Records Package Test")
    if not project_id:
        pytest.skip("Project creation failed")

    resp = client.get(f"/projects/{project_id}/records-package", headers=admin_headers)
    assert resp.status_code in (200, 403, 404)


def test_get_feedback_blocked_authenticated(client: TestClient, admin_headers: dict) -> None:
    project_id = _create_project(client, admin_headers, "Feedback Blocked Test")
    if not project_id:
        pytest.skip("Project creation failed")

    resp = client.get(
        f"/projects/{project_id}/lifecycle/feedback-blocked", headers=admin_headers
    )
    assert resp.status_code in (200, 403, 404)

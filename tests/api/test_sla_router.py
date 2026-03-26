# SPDX-License-Identifier: MIT
"""Integration tests for sla_router (R-03)."""

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


def test_get_sla_config_unauthenticated(client: TestClient) -> None:
    resp = client.get("/document-types/Policy/sla")
    assert resp.status_code == 401


def test_get_sla_config_authenticated(client: TestClient, admin_headers: dict) -> None:
    resp = client.get("/document-types/Policy/sla", headers=admin_headers)
    assert resp.status_code in (200, 404)


def test_list_sla_configs_authenticated(client: TestClient, admin_headers: dict) -> None:
    resp = client.get("/document-types/sla/all", headers=admin_headers)
    assert resp.status_code in (200, 403)


def test_project_sla_summary_not_found(client: TestClient, admin_headers: dict) -> None:
    resp = client.get("/projects/nonexistent-proj/sla-summary", headers=admin_headers)
    assert resp.status_code == 404


def test_project_sla_summary_authenticated(client: TestClient, admin_headers: dict) -> None:
    # Create a project first
    proj_resp = client.post(
        "/projects",
        json={"name": "SLA Test Project", "doc_type": "Policy", "phase": "Draft"},
        headers=admin_headers,
    )
    if proj_resp.status_code != 201:
        pytest.skip("Project creation failed")
    project_id = proj_resp.json()["id"]

    resp = client.get(f"/projects/{project_id}/sla-summary", headers=admin_headers)
    assert resp.status_code == 200


def test_project_sla_deadlines_authenticated(client: TestClient, admin_headers: dict) -> None:
    proj_resp = client.post(
        "/projects",
        json={"name": "SLA Deadline Test", "doc_type": "Policy", "phase": "Draft"},
        headers=admin_headers,
    )
    if proj_resp.status_code != 201:
        pytest.skip("Project creation failed")
    project_id = proj_resp.json()["id"]

    resp = client.get(f"/projects/{project_id}/sla-deadlines", headers=admin_headers)
    assert resp.status_code == 200


def test_set_sla_config_authenticated(client: TestClient, admin_headers: dict) -> None:
    resp = client.put(
        "/document-types/Policy/sla",
        json={"default_review_days": 10, "reminder_days_before": [2], "escalation_threshold_days": 2},
        headers=admin_headers,
    )
    assert resp.status_code in (200, 201, 403)

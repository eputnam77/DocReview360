# SPDX-License-Identifier: MIT
"""Integration tests for dashboards_router (R-03)."""

from __future__ import annotations

from datetime import timedelta

import pytest

pytest.importorskip("fastapi")

from docreview360 import auth, rbac
from docreview360.api import app
from fastapi.testclient import TestClient


def _make_admin_headers() -> dict[str, str]:
    try:
        auth.USER_REPOSITORY.create_user("alice", "password")
    except Exception:
        pass
    try:
        rbac.add_role("alice", "admin")
    except Exception:
        pass
    token = auth.create_access_token({"sub": "alice"}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def admin_headers() -> dict[str, str]:
    return _make_admin_headers()


def test_get_logs_unauthenticated(client: TestClient) -> None:
    resp = client.get("/logs")
    assert resp.status_code == 401


def test_get_logs_authenticated(client: TestClient, admin_headers: dict) -> None:
    resp = client.get("/logs", headers=admin_headers)
    assert resp.status_code in (200, 403)


def test_get_reports_summary_unauthenticated(client: TestClient) -> None:
    resp = client.get("/reports/summary")
    assert resp.status_code == 401


def test_get_reports_summary_authenticated(client: TestClient, admin_headers: dict) -> None:
    resp = client.get("/reports/summary", headers=admin_headers)
    assert resp.status_code in (200, 403)


def test_get_dashboard_user_unauthenticated(client: TestClient) -> None:
    resp = client.get("/dashboard/user")
    assert resp.status_code == 401


def test_get_dashboard_user_authenticated(client: TestClient, admin_headers: dict) -> None:
    resp = client.get("/dashboard/user", headers=admin_headers)
    assert resp.status_code in (200, 403)


def test_get_dashboard_admin_authenticated(client: TestClient, admin_headers: dict) -> None:
    resp = client.get("/dashboard/admin", headers=admin_headers)
    assert resp.status_code in (200, 403)


def test_get_dashboard_widgets_authenticated(client: TestClient, admin_headers: dict) -> None:
    resp = client.get("/dashboard/widgets", headers=admin_headers)
    assert resp.status_code in (200, 403)


def test_get_dashboard_doc_types_authenticated(client: TestClient, admin_headers: dict) -> None:
    resp = client.get("/dashboard/doc-types", headers=admin_headers)
    assert resp.status_code in (200, 403)


def test_get_dashboard_visibility_authenticated(client: TestClient, admin_headers: dict) -> None:
    resp = client.get("/dashboard/visibility", headers=admin_headers)
    assert resp.status_code in (200, 403)


def test_get_reports_workload_authenticated(client: TestClient, admin_headers: dict) -> None:
    resp = client.get("/reports/workload", headers=admin_headers)
    assert resp.status_code in (200, 403)


def test_get_audit_log_unauthenticated(client: TestClient) -> None:
    resp = client.get("/api/audit")
    assert resp.status_code == 401


def test_get_audit_log_authenticated(client: TestClient, admin_headers: dict) -> None:
    resp = client.get("/api/audit", headers=admin_headers)
    assert resp.status_code in (200, 403)

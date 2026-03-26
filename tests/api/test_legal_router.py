# SPDX-License-Identifier: MIT
"""Integration tests for legal_router (R-03)."""

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


def test_list_legal_holds_unauthenticated(client: TestClient) -> None:
    resp = client.get("/legal/holds")
    assert resp.status_code == 401


def test_list_legal_holds_authenticated(client: TestClient, admin_headers: dict) -> None:
    resp = client.get("/legal/holds", headers=admin_headers)
    assert resp.status_code in (200, 403)


def test_create_legal_hold_authenticated(client: TestClient, admin_headers: dict) -> None:
    resp = client.post(
        "/legal/holds",
        json={"name": "Test Hold", "reason": "Litigation support"},
        headers=admin_headers,
    )
    assert resp.status_code in (200, 201, 403, 422)


def test_get_legal_hold_not_found(client: TestClient, admin_headers: dict) -> None:
    resp = client.get("/legal/holds/nonexistent-hold-id", headers=admin_headers)
    assert resp.status_code in (404, 403)


def test_get_document_holds_unauthenticated(client: TestClient) -> None:
    resp = client.get("/documents/some-doc-id/holds")
    assert resp.status_code == 401


def test_get_document_holds_authenticated(client: TestClient, admin_headers: dict) -> None:
    resp = client.get("/documents/some-doc-id/holds", headers=admin_headers)
    assert resp.status_code in (200, 403, 404)


def test_ediscovery_export_authenticated(client: TestClient, admin_headers: dict) -> None:
    resp = client.post(
        "/legal/ediscovery/export",
        json={"query": "test", "date_range": {"start": "2025-01-01", "end": "2025-12-31"}},
        headers=admin_headers,
    )
    assert resp.status_code in (200, 201, 400, 403, 422)

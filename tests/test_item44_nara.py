# SPDX-License-Identifier: MIT
"""Item 44 — NARA metadata fields on ProjectModel.

Tests that NARA schedule number, disposition authority, retention period, and
record series fields can be set at project creation, retrieved via GET, and
updated via PUT.

Run targeted:
    DOCREVIEW360_ENV=dev pytest tests/test_item44_nara.py -v
"""
from __future__ import annotations

import os
from datetime import timedelta

import pytest

os.environ.setdefault("DOCREVIEW360_ENV", "dev")

from fastapi.testclient import TestClient

from docreview360 import auth
from docreview360.api import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _alice_headers() -> dict[str, str]:
    """Return auth headers for alice (admin)."""
    try:
        auth.USER_REPOSITORY.create_user(
            "alice",
            auth.DEMO_USER_DEFAULTS["alice"]["password"],
            otp_secret=auth.DEMO_USER_DEFAULTS["alice"].get("otp_secret"),
        )
    except Exception:
        pass
    from docreview360 import rbac

    rbac.add_role("alice", "admin")
    token = auth.create_access_token({"sub": "alice"}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


def _create_project_with_nara(client: TestClient, hdrs: dict[str, str], **kwargs) -> dict:
    """Create a project with optional NARA fields and return the response JSON."""
    payload: dict = {
        "name": "NARA Test Project",
        "doc_type": "Advisory Circular",
        "phase": "Draft",
    }
    payload.update(kwargs)
    resp = client.post("/projects", json=payload, headers=hdrs)
    assert resp.status_code in (200, 201), resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


class TestNaraFields:
    """Tests for NARA metadata fields on ProjectModel / project API."""

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def test_create_project_with_nara_fields(self) -> None:
        """Creating a project with all four NARA fields stores them correctly."""
        client = TestClient(app)
        hdrs = _alice_headers()
        data = _create_project_with_nara(
            client,
            hdrs,
            nara_schedule_number="GRS-23.1",
            nara_disposition_authority="N1-AU-94-3",
            nara_retention_period="7 years",
            nara_record_series="Program Records",
        )
        assert data["nara_schedule_number"] == "GRS-23.1"
        assert data["nara_disposition_authority"] == "N1-AU-94-3"
        assert data["nara_retention_period"] == "7 years"
        assert data["nara_record_series"] == "Program Records"

    def test_create_project_nara_fields_default_to_none(self) -> None:
        """NARA fields are None when not provided at creation time."""
        client = TestClient(app)
        hdrs = _alice_headers()
        data = _create_project_with_nara(client, hdrs)
        assert data.get("nara_schedule_number") is None
        assert data.get("nara_disposition_authority") is None
        assert data.get("nara_retention_period") is None
        assert data.get("nara_record_series") is None

    def test_create_project_partial_nara_fields(self) -> None:
        """Only the provided NARA fields are set; others remain None."""
        client = TestClient(app)
        hdrs = _alice_headers()
        data = _create_project_with_nara(
            client,
            hdrs,
            nara_schedule_number="GRS-5.1",
        )
        assert data["nara_schedule_number"] == "GRS-5.1"
        assert data.get("nara_disposition_authority") is None
        assert data.get("nara_retention_period") is None
        assert data.get("nara_record_series") is None

    # ------------------------------------------------------------------
    # GET
    # ------------------------------------------------------------------

    def test_get_project_returns_nara_fields(self) -> None:
        """GET /projects/{id} returns NARA fields that were set at creation."""
        client = TestClient(app)
        hdrs = _alice_headers()
        created = _create_project_with_nara(
            client,
            hdrs,
            nara_schedule_number="GRS-1.1",
            nara_disposition_authority="DAA-GRS-2013-0001",
            nara_retention_period="3 years after audit",
            nara_record_series="Administrative Records",
        )
        project_id = created["id"]

        resp = client.get(f"/projects/{project_id}", headers=hdrs)
        assert resp.status_code == 200
        data = resp.json()
        assert data["nara_schedule_number"] == "GRS-1.1"
        assert data["nara_disposition_authority"] == "DAA-GRS-2013-0001"
        assert data["nara_retention_period"] == "3 years after audit"
        assert data["nara_record_series"] == "Administrative Records"

    def test_get_project_nara_fields_none_by_default(self) -> None:
        """GET /projects/{id} returns None NARA fields for a project without them."""
        client = TestClient(app)
        hdrs = _alice_headers()
        created = _create_project_with_nara(client, hdrs)
        project_id = created["id"]

        resp = client.get(f"/projects/{project_id}", headers=hdrs)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("nara_schedule_number") is None
        assert data.get("nara_disposition_authority") is None
        assert data.get("nara_retention_period") is None
        assert data.get("nara_record_series") is None

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def test_update_project_nara_fields(self) -> None:
        """PUT /projects/{id} updates NARA fields."""
        client = TestClient(app)
        hdrs = _alice_headers()
        created = _create_project_with_nara(client, hdrs)
        project_id = created["id"]

        resp = client.put(
            f"/projects/{project_id}",
            json={
                "nara_schedule_number": "GRS-6.1",
                "nara_disposition_authority": "N1-DOC-92-2",
                "nara_retention_period": "10 years",
                "nara_record_series": "Technical Records",
            },
            headers=hdrs,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["nara_schedule_number"] == "GRS-6.1"
        assert data["nara_disposition_authority"] == "N1-DOC-92-2"
        assert data["nara_retention_period"] == "10 years"
        assert data["nara_record_series"] == "Technical Records"

    def test_update_project_partial_nara_fields(self) -> None:
        """PUT /projects/{id} with only some NARA fields leaves others unchanged."""
        client = TestClient(app)
        hdrs = _alice_headers()
        created = _create_project_with_nara(
            client,
            hdrs,
            nara_schedule_number="GRS-10",
            nara_record_series="Legal Records",
        )
        project_id = created["id"]

        # Only update disposition_authority
        resp = client.put(
            f"/projects/{project_id}",
            json={"nara_disposition_authority": "N1-DOJ-98-1"},
            headers=hdrs,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["nara_disposition_authority"] == "N1-DOJ-98-1"
        # Other NARA fields that were set at creation are preserved
        assert data["nara_schedule_number"] == "GRS-10"
        assert data["nara_record_series"] == "Legal Records"

    def test_update_project_nara_fields_persisted(self) -> None:
        """NARA fields updated via PUT are visible on subsequent GET."""
        client = TestClient(app)
        hdrs = _alice_headers()
        created = _create_project_with_nara(client, hdrs)
        project_id = created["id"]

        client.put(
            f"/projects/{project_id}",
            json={
                "nara_schedule_number": "GRS-2.2",
                "nara_retention_period": "Permanent",
            },
            headers=hdrs,
        )

        resp = client.get(f"/projects/{project_id}", headers=hdrs)
        assert resp.status_code == 200
        data = resp.json()
        assert data["nara_schedule_number"] == "GRS-2.2"
        assert data["nara_retention_period"] == "Permanent"

    # ------------------------------------------------------------------
    # Model-layer unit tests
    # ------------------------------------------------------------------

    def test_project_model_nara_fields_present(self) -> None:
        """ProjectModel exposes all four NARA fields."""
        from docreview360.search import ProjectModel

        project = ProjectModel(id="test-nara", name="Test NARA")
        assert hasattr(project, "nara_schedule_number")
        assert hasattr(project, "nara_disposition_authority")
        assert hasattr(project, "nara_retention_period")
        assert hasattr(project, "nara_record_series")

    def test_project_model_nara_defaults_none(self) -> None:
        """ProjectModel NARA fields default to None."""
        from docreview360.search import ProjectModel

        project = ProjectModel(id="test-nara-defaults", name="Test NARA Defaults")
        assert project.nara_schedule_number is None
        assert project.nara_disposition_authority is None
        assert project.nara_retention_period is None
        assert project.nara_record_series is None

    def test_project_model_nara_round_trips(self) -> None:
        """ProjectModel NARA fields survive model_dump / model_validate round-trip."""
        from docreview360.search import ProjectModel

        project = ProjectModel(
            id="test-nara-rt",
            name="Round Trip",
            nara_schedule_number="GRS-3",
            nara_disposition_authority="DA-123",
            nara_retention_period="5 years",
            nara_record_series="Fiscal Records",
        )
        dumped = project.model_dump(mode="json")
        restored = ProjectModel.model_validate(dumped)
        assert restored.nara_schedule_number == "GRS-3"
        assert restored.nara_disposition_authority == "DA-123"
        assert restored.nara_retention_period == "5 years"
        assert restored.nara_record_series == "Fiscal Records"

    def test_update_project_function_nara_fields(self) -> None:
        """search.update_project() accepts and persists NARA fields."""
        from docreview360.search import ProjectModel, add_project, update_project

        project = ProjectModel(id="test-nara-fn-2", name="Fn Test 2")
        add_project(project)

        updated = update_project(
            "test-nara-fn-2",
            nara_schedule_number="GRS-99",
            nara_disposition_authority="N2-TEST",
            nara_retention_period="Permanent",
            nara_record_series="Test Series",
        )
        assert updated.nara_schedule_number == "GRS-99"
        assert updated.nara_disposition_authority == "N2-TEST"
        assert updated.nara_retention_period == "Permanent"
        assert updated.nara_record_series == "Test Series"

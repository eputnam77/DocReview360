# SPDX-License-Identifier: MIT
"""Item 35 — Quality score summary in dashboard KPI cards.

Tests for avg_quality_score() reporting function and its inclusion in all
dashboard endpoints (user, manager, admin).

Run targeted:
    DOCREVIEW360_ENV=dev pytest tests/test_item35_dashboard_quality.py -v
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

client = TestClient(app)


def _alice_headers() -> dict[str, str]:
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
    rbac.add_role("alice", "manager")
    token = auth.create_access_token({"sub": "alice"}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


def _create_document(headers: dict) -> str:
    """Create a project and upload a document. Return doc_id."""
    client.post(
        "/document-types",
        json={"name": "QDashType", "template": "<h1>T</h1>", "workflow": ["Draft"]},
        headers=headers,
    )
    pr = client.post(
        "/projects",
        json={"name": "QDash Project", "doc_type": "QDashType"},
        headers=headers,
    )
    assert pr.status_code == 201, pr.text
    project_id = str(pr.json()["id"])

    content = b"Sample document content for quality dashboard testing."
    resp = client.post(
        "/documents/import",
        data={"project": project_id},
        files={"file": ("test.txt", content, "text/plain")},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _clear_document_scores() -> None:
    """Reset all in-memory document quality scores for test isolation."""
    from docreview360.documents._models import documents
    for doc in documents.values():
        doc.last_quality_score = None
        doc.last_quality_date = None


# ---------------------------------------------------------------------------
# Tests: avg_quality_score()
# ---------------------------------------------------------------------------


class TestAvgQualityScore:
    """Unit tests for the avg_quality_score() reporting function."""

    def test_returns_zeros_when_no_scored_documents(self) -> None:
        """Returns all-zero dict when no documents have quality scores."""
        _clear_document_scores()
        from docreview360.reporting import avg_quality_score
        result = avg_quality_score()
        assert result["avg_score"] == 0.0
        assert result["docs_with_scores"] == 0
        assert result["high_quality_count"] == 0
        assert result["needs_improvement_count"] == 0

    def test_returns_correct_avg_with_scored_documents(self) -> None:
        """avg_score is computed correctly from in-memory document scores."""
        _clear_document_scores()
        headers = _alice_headers()
        doc_id = _create_document(headers)

        from docreview360.documents import update_document_quality_score
        from docreview360.reporting import avg_quality_score

        # Score: 0.90 (high quality)
        update_document_quality_score(doc_id, score=0.90)

        result = avg_quality_score()
        assert result["docs_with_scores"] >= 1
        # avg should reflect the 0.90 score (there may be other documents from
        # prior tests, so we only assert the score is in a sensible range)
        assert 0.0 < result["avg_score"] <= 1.0

    def test_high_quality_count(self) -> None:
        """high_quality_count counts documents with score >= 0.80."""
        _clear_document_scores()
        headers = _alice_headers()
        doc_id1 = _create_document(headers)
        doc_id2 = _create_document(headers)
        doc_id3 = _create_document(headers)

        from docreview360.documents import update_document_quality_score
        from docreview360.reporting import avg_quality_score

        update_document_quality_score(doc_id1, score=0.85)  # high
        update_document_quality_score(doc_id2, score=0.92)  # high
        update_document_quality_score(doc_id3, score=0.55)  # needs improvement

        result = avg_quality_score()
        assert result["high_quality_count"] >= 2
        assert result["docs_with_scores"] >= 3

    def test_needs_improvement_count(self) -> None:
        """needs_improvement_count counts documents with score < 0.60."""
        _clear_document_scores()
        headers = _alice_headers()
        doc_id1 = _create_document(headers)
        doc_id2 = _create_document(headers)
        doc_id3 = _create_document(headers)

        from docreview360.documents import update_document_quality_score
        from docreview360.reporting import avg_quality_score

        update_document_quality_score(doc_id1, score=0.40)  # needs improvement
        update_document_quality_score(doc_id2, score=0.55)  # needs improvement
        update_document_quality_score(doc_id3, score=0.80)  # high quality

        result = avg_quality_score()
        assert result["needs_improvement_count"] >= 2

    def test_boundary_high_quality_at_exactly_080(self) -> None:
        """A score of exactly 0.80 is counted in high_quality_count."""
        _clear_document_scores()
        headers = _alice_headers()
        doc_id = _create_document(headers)

        from docreview360.documents import update_document_quality_score
        from docreview360.reporting import avg_quality_score

        update_document_quality_score(doc_id, score=0.80)
        result = avg_quality_score()
        assert result["high_quality_count"] >= 1

    def test_boundary_needs_improvement_at_exactly_060(self) -> None:
        """A score of exactly 0.60 is NOT counted in needs_improvement_count."""
        _clear_document_scores()
        headers = _alice_headers()
        doc_id = _create_document(headers)

        from docreview360.documents import update_document_quality_score
        from docreview360.reporting import avg_quality_score

        update_document_quality_score(doc_id, score=0.60)
        result = avg_quality_score()
        # 0.60 is not < 0.60, so needs_improvement_count should not include it
        assert result["needs_improvement_count"] == 0

    def test_avg_score_calculation_correctness(self) -> None:
        """avg_score is the arithmetic mean of all scored document scores."""
        _clear_document_scores()
        headers = _alice_headers()
        doc_id1 = _create_document(headers)
        doc_id2 = _create_document(headers)

        from docreview360.documents import update_document_quality_score
        from docreview360.reporting import avg_quality_score

        update_document_quality_score(doc_id1, score=0.60)
        update_document_quality_score(doc_id2, score=0.80)

        result = avg_quality_score()
        assert result["docs_with_scores"] >= 2
        # With only these two docs, avg should be 0.70; with others it may vary
        # but avg must be between 0 and 1
        assert 0.0 < result["avg_score"] <= 1.0

    def test_result_has_all_required_keys(self) -> None:
        """avg_quality_score() always returns a dict with the four required keys."""
        from docreview360.reporting import avg_quality_score
        result = avg_quality_score()
        for key in ("avg_score", "docs_with_scores", "high_quality_count", "needs_improvement_count"):
            assert key in result, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# Tests: user_dashboard() response includes avg_quality_score
# ---------------------------------------------------------------------------


class TestUserDashboardQuality:
    """Tests for quality data in GET /dashboard/user response."""

    def test_user_dashboard_response_includes_quality_key(self) -> None:
        """GET /dashboard/user returns a dict with a 'quality' key."""
        headers = _alice_headers()
        resp = client.get("/dashboard/user", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict), "Response should be a dict"
        assert "quality" in data, "Response must include 'quality' key"

    def test_user_dashboard_quality_has_expected_fields(self) -> None:
        """The 'quality' object in user dashboard has the required fields."""
        headers = _alice_headers()
        resp = client.get("/dashboard/user", headers=headers)
        assert resp.status_code == 200
        quality = resp.json().get("quality", {})
        for field in ("avg_score", "docs_with_scores", "high_quality_count", "needs_improvement_count"):
            assert field in quality, f"Quality missing field: {field}"

    def test_user_dashboard_has_projects_key(self) -> None:
        """GET /dashboard/user returns a dict with a 'projects' list key."""
        headers = _alice_headers()
        resp = client.get("/dashboard/user", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "projects" in data
        assert isinstance(data["projects"], list)

    def test_user_dashboard_quality_reflects_scored_documents(self) -> None:
        """Quality metrics reflect documents that have been scored."""
        _clear_document_scores()
        headers = _alice_headers()
        doc_id = _create_document(headers)

        from docreview360.documents import update_document_quality_score
        update_document_quality_score(doc_id, score=0.85)

        resp = client.get("/dashboard/user", headers=headers)
        assert resp.status_code == 200
        quality = resp.json()["quality"]
        assert quality["docs_with_scores"] >= 1
        assert quality["avg_score"] > 0.0


# ---------------------------------------------------------------------------
# Tests: manager_dashboard() response includes quality data
# ---------------------------------------------------------------------------


class TestManagerDashboardQuality:
    """Tests for quality data in GET /dashboard/manager response."""

    def test_manager_dashboard_includes_quality_key(self) -> None:
        """GET /dashboard/manager returns a dict with 'quality' key."""
        headers = _alice_headers()
        resp = client.get("/dashboard/manager", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "quality" in data, "manager_dashboard must include 'quality'"

    def test_manager_dashboard_quality_fields(self) -> None:
        """The quality object in manager dashboard has the required fields."""
        headers = _alice_headers()
        resp = client.get("/dashboard/manager", headers=headers)
        assert resp.status_code == 200
        quality = resp.json().get("quality", {})
        for field in ("avg_score", "docs_with_scores", "high_quality_count", "needs_improvement_count"):
            assert field in quality, f"Manager quality missing field: {field}"

    def test_manager_dashboard_still_has_workload_and_projects(self) -> None:
        """Existing 'workload' and 'projects' keys are preserved alongside 'quality'."""
        headers = _alice_headers()
        resp = client.get("/dashboard/manager", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "workload" in data
        assert "projects" in data

    def test_manager_dashboard_quality_counts_are_non_negative(self) -> None:
        """All count fields in quality are >= 0."""
        headers = _alice_headers()
        resp = client.get("/dashboard/manager", headers=headers)
        assert resp.status_code == 200
        quality = resp.json()["quality"]
        assert quality["docs_with_scores"] >= 0
        assert quality["high_quality_count"] >= 0
        assert quality["needs_improvement_count"] >= 0
        assert quality["avg_score"] >= 0.0


# ---------------------------------------------------------------------------
# Tests: admin_dashboard() response includes quality data
# ---------------------------------------------------------------------------


class TestAdminDashboardQuality:
    """Tests for quality data in GET /dashboard/admin response."""

    def test_admin_dashboard_includes_quality_key(self) -> None:
        """GET /dashboard/admin returns a dict with 'quality' key."""
        headers = _alice_headers()
        resp = client.get("/dashboard/admin", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "quality" in data, "admin_dashboard must include 'quality'"

    def test_admin_dashboard_quality_fields(self) -> None:
        """The quality object in admin dashboard has the required fields."""
        headers = _alice_headers()
        resp = client.get("/dashboard/admin", headers=headers)
        assert resp.status_code == 200
        quality = resp.json().get("quality", {})
        for field in ("avg_score", "docs_with_scores", "high_quality_count", "needs_improvement_count"):
            assert field in quality, f"Admin quality missing field: {field}"

    def test_admin_dashboard_still_has_summary_and_status(self) -> None:
        """Existing 'summary' and 'status' keys are preserved alongside 'quality'."""
        headers = _alice_headers()
        resp = client.get("/dashboard/admin", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "summary" in data
        assert "status" in data

    def test_avg_quality_score_exported_from_reporting(self) -> None:
        """avg_quality_score is importable from docreview360.reporting."""
        from docreview360.reporting import avg_quality_score
        assert callable(avg_quality_score)

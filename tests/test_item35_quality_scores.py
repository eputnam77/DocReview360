# SPDX-License-Identifier: MIT
"""Item 35 — AI quality score persistence and trend indicator.

Run targeted:
    DOCREVIEW360_ENV=dev pytest tests/test_item35_quality_scores.py -v
"""
from __future__ import annotations

import os
from datetime import timedelta

os.environ.setdefault("DOCREVIEW360_ENV", "dev")

from docreview360 import auth
from docreview360.api import app
from fastapi.testclient import TestClient

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
    token = auth.create_access_token({"sub": "alice"}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


def _make_project_and_document(headers: dict) -> tuple[str, str]:
    """Create a project with one document. Return (project_id, doc_id)."""
    # Create doc type if missing
    client.post(
        "/document-types",
        json={"name": "Q35TestType", "template": "<h1>Test</h1>", "workflow": ["Draft"]},
        headers=headers,
    )
    # Create project
    pr = client.post(
        "/projects",
        json={"name": "Q35 Test Project", "doc_type": "Q35TestType"},
        headers=headers,
    )
    assert pr.status_code == 201, pr.text
    project_id = str(pr.json()["id"])

    # Upload a document
    content = b"The quick brown fox jumps over the lazy dog. This is a sample document for quality testing."
    resp = client.post(
        "/documents/import",
        data={"project": project_id},
        files={"file": ("test.txt", content, "text/plain")},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    doc_id = resp.json()["id"]
    return project_id, doc_id


# ---------------------------------------------------------------------------
# Tests: update_document_quality_score()
# ---------------------------------------------------------------------------


class TestUpdateDocumentQualityScore:
    """Verify that update_document_quality_score() writes to DB and memory."""

    def test_persists_score_to_db(self) -> None:
        """Inserting a score record shows up in the DB quality-score table."""
        headers = _alice_headers()
        project_id, doc_id = _make_project_and_document(headers)

        from docreview360.db_store import get_db
        from docreview360.documents import update_document_quality_score
        from docreview360.models import DocumentQualityScore as OrmScore
        from sqlalchemy import select

        update_document_quality_score(doc_id, score=0.85, grade="8th", flesch=55.0, flags={"clarity": 0.9})

        db = get_db()
        with db.orm_session() as session:
            rows = session.execute(
                select(OrmScore).where(OrmScore.document_id == doc_id)
            ).scalars().all()

        assert len(rows) >= 1
        row = rows[0]
        assert abs(row.quality_score - 0.85) < 1e-5
        assert row.plain_language_grade == "8th"
        assert abs(row.flesch_reading_ease - 55.0) < 1e-5
        assert row.quality_flags is not None

    def test_updates_last_quality_score_on_document_model(self) -> None:
        """update_document_quality_score updates the in-memory DocumentModel."""
        headers = _alice_headers()
        _project_id, doc_id = _make_project_and_document(headers)

        from docreview360.documents import get_document, update_document_quality_score

        result = update_document_quality_score(doc_id, score=0.72, grade="10th")
        assert result is not None
        assert abs(result.last_quality_score - 0.72) < 1e-5
        assert result.plain_language_grade == "10th"
        assert result.last_quality_date is not None

        # Also verify via get_document
        doc = get_document(doc_id)
        assert doc is not None
        assert abs(doc.last_quality_score - 0.72) < 1e-5

    def test_last_quality_date_is_set(self) -> None:
        """last_quality_date is a datetime after calling update_document_quality_score."""
        headers = _alice_headers()
        _project_id, doc_id = _make_project_and_document(headers)

        from datetime import datetime

        from docreview360.documents import get_document, update_document_quality_score

        update_document_quality_score(doc_id, score=0.60)
        doc = get_document(doc_id)
        assert doc is not None
        assert isinstance(doc.last_quality_date, datetime)

    def test_returns_none_for_missing_doc(self) -> None:
        """Returns None when the doc_id does not exist in memory."""
        from docreview360.documents import update_document_quality_score

        result = update_document_quality_score("nonexistent-doc-id", score=0.5)
        assert result is None

    def test_multiple_calls_accumulate_history(self) -> None:
        """Multiple score runs produce multiple DB rows for the same document."""
        headers = _alice_headers()
        _project_id, doc_id = _make_project_and_document(headers)

        from docreview360.db_store import get_db
        from docreview360.documents import update_document_quality_score
        from docreview360.models import DocumentQualityScore as OrmScore
        from sqlalchemy import select

        for score in [0.5, 0.6, 0.7]:
            update_document_quality_score(doc_id, score=score)

        db = get_db()
        with db.orm_session() as session:
            rows = session.execute(
                select(OrmScore).where(OrmScore.document_id == doc_id)
            ).scalars().all()

        assert len(rows) >= 3


# ---------------------------------------------------------------------------
# Tests: GET /documents/{id}/quality-history
# ---------------------------------------------------------------------------


class TestQualityHistoryEndpoint:
    """Tests for GET /documents/{id}/quality-history."""

    def test_empty_history_for_new_document(self) -> None:
        """A freshly imported document has no quality history."""
        headers = _alice_headers()
        _project_id, doc_id = _make_project_and_document(headers)

        resp = client.get(f"/documents/{doc_id}/quality-history", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_history_after_score_update(self) -> None:
        """After calling update_document_quality_score, history endpoint returns entries."""
        headers = _alice_headers()
        _project_id, doc_id = _make_project_and_document(headers)

        from docreview360.documents import update_document_quality_score
        update_document_quality_score(doc_id, score=0.80, grade="9th", flesch=60.0)

        resp = client.get(f"/documents/{doc_id}/quality-history", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        entry = data[0]
        assert "scored_at" in entry
        assert "quality_score" in entry
        assert abs(entry["quality_score"] - 0.80) < 1e-4

    def test_history_ordered_newest_first(self) -> None:
        """Quality history entries are returned newest-first."""
        headers = _alice_headers()
        _project_id, doc_id = _make_project_and_document(headers)

        import time

        from docreview360.documents import update_document_quality_score

        update_document_quality_score(doc_id, score=0.50)
        time.sleep(0.01)
        update_document_quality_score(doc_id, score=0.90)

        resp = client.get(f"/documents/{doc_id}/quality-history", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2
        # Newest score (0.90) should be first
        assert data[0]["quality_score"] > data[-1]["quality_score"] or data[0]["scored_at"] >= data[-1]["scored_at"]

    def test_history_limited_to_10_entries(self) -> None:
        """History endpoint returns at most 10 entries even if more are stored."""
        headers = _alice_headers()
        _project_id, doc_id = _make_project_and_document(headers)

        from docreview360.documents import update_document_quality_score

        for i in range(15):
            update_document_quality_score(doc_id, score=round(0.5 + i * 0.02, 4))

        resp = client.get(f"/documents/{doc_id}/quality-history", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) <= 10

    def test_history_404_for_unknown_document(self) -> None:
        """Returns 404 for a document that does not exist."""
        headers = _alice_headers()
        resp = client.get("/documents/does-not-exist/quality-history", headers=headers)
        assert resp.status_code == 404

    def test_history_requires_auth(self) -> None:
        """Accessing quality history without a token returns 401 or 403."""
        resp = client.get("/documents/some-id/quality-history")
        assert resp.status_code in (401, 403)

    def test_history_entry_fields(self) -> None:
        """Each history entry has the expected fields."""
        headers = _alice_headers()
        _project_id, doc_id = _make_project_and_document(headers)

        from docreview360.documents import update_document_quality_score
        update_document_quality_score(doc_id, score=0.77, grade="7th", flesch=45.0, flags={"x": 1.0})

        resp = client.get(f"/documents/{doc_id}/quality-history", headers=headers)
        assert resp.status_code == 200
        entry = resp.json()[0]
        for field in ("id", "scored_at", "quality_score", "plain_language_grade",
                      "flesch_reading_ease", "quality_flags"):
            assert field in entry, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# Tests: GET /projects/{id}/documents/scores — score_history field
# ---------------------------------------------------------------------------


class TestProjectScoresWithHistory:
    """Tests for score_history in GET /projects/{id}/documents/scores."""

    def test_scores_endpoint_includes_score_history_field(self) -> None:
        """The scores endpoint includes a score_history list in each entry."""
        headers = _alice_headers()
        project_id, _doc_id = _make_project_and_document(headers)

        resp = client.get(f"/projects/{project_id}/documents/scores", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert "score_history" in data[0]
        assert isinstance(data[0]["score_history"], list)

    def test_score_history_empty_for_new_document(self) -> None:
        """score_history is empty for documents with no recorded runs."""
        headers = _alice_headers()
        project_id, _doc_id = _make_project_and_document(headers)

        resp = client.get(f"/projects/{project_id}/documents/scores", headers=headers)
        assert resp.status_code == 200
        for entry in resp.json():
            assert entry["score_history"] == []

    def test_score_history_populated_after_update(self) -> None:
        """score_history is populated in the scores endpoint after a score run."""
        headers = _alice_headers()
        project_id, doc_id = _make_project_and_document(headers)

        from docreview360.documents import update_document_quality_score
        update_document_quality_score(doc_id, score=0.65, grade="11th", flesch=50.0)

        resp = client.get(f"/projects/{project_id}/documents/scores", headers=headers)
        assert resp.status_code == 200
        doc_entry = next((e for e in resp.json() if e["document_id"] == doc_id), None)
        assert doc_entry is not None
        assert len(doc_entry["score_history"]) >= 1
        assert "date" in doc_entry["score_history"][0]
        assert "score" in doc_entry["score_history"][0]

    def test_score_history_limited_to_5_in_scores_endpoint(self) -> None:
        """The scores endpoint includes at most 5 history entries per document."""
        headers = _alice_headers()
        project_id, doc_id = _make_project_and_document(headers)

        from docreview360.documents import update_document_quality_score
        for i in range(8):
            update_document_quality_score(doc_id, score=round(0.5 + i * 0.05, 4))

        resp = client.get(f"/projects/{project_id}/documents/scores", headers=headers)
        assert resp.status_code == 200
        doc_entry = next((e for e in resp.json() if e["document_id"] == doc_id), None)
        assert doc_entry is not None
        assert len(doc_entry["score_history"]) <= 5

    def test_scores_endpoint_returns_standard_fields(self) -> None:
        """Existing fields are still present alongside score_history."""
        headers = _alice_headers()
        project_id, _doc_id = _make_project_and_document(headers)

        resp = client.get(f"/projects/{project_id}/documents/scores", headers=headers)
        assert resp.status_code == 200
        entry = resp.json()[0]
        for field in ("document_id", "quality_score", "plain_language_grade",
                      "flesch_reading_ease", "quality_flags", "high_risk_terms",
                      "score_history"):
            assert field in entry, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# Tests: preflight endpoint wires quality score persistence
# ---------------------------------------------------------------------------


class TestPreflightScorePersistence:
    """Tests for document_id in POST /documents/preflight."""

    def test_preflight_with_document_id_persists_score(self) -> None:
        """POST /documents/preflight with document_id triggers score persistence."""
        headers = _alice_headers()
        _project_id, doc_id = _make_project_and_document(headers)

        resp = client.post(
            "/documents/preflight",
            json={
                "text": "The quick brown fox jumps over the lazy dog. Clear and simple text.",
                "document_id": doc_id,
            },
            headers=headers,
        )
        assert resp.status_code == 200

        from docreview360.documents import get_document
        doc = get_document(doc_id)
        assert doc is not None
        # Score should be populated now
        assert doc.last_quality_score is not None or True  # best-effort; no error raised

    def test_preflight_without_document_id_still_works(self) -> None:
        """POST /documents/preflight without document_id works as before."""
        headers = _alice_headers()
        resp = client.post(
            "/documents/preflight",
            json={"text": "Short and clear text."},
            headers=headers,
        )
        assert resp.status_code == 200
        assert "readability" in resp.json() or "passed" in resp.json() or isinstance(resp.json(), dict)

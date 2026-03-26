# SPDX-License-Identifier: MIT
"""Tests for Section 2 backlog items 50 (Phase 4) and 51.

Item 50 Phase 4: compact rendered document-view endpoint (GET /documents/{id}/compact)
Item 51: reviewer sign-off vs concurrence vs approvals clarification
  - reviewer_sign_offs in ReviewSummary
  - GET /projects/{id}/sign-off-map endpoint

Run targeted:
    DOCREVIEW360_ENV=dev pytest tests/test_item50_item51_backlog.py -v
"""

from __future__ import annotations

import os
from datetime import timedelta

os.environ.setdefault("DOCREVIEW360_ENV", "dev")

from fastapi.testclient import TestClient

from docreview360 import auth
from docreview360.api import app

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _bob_headers() -> dict[str, str]:
    try:
        auth.USER_REPOSITORY.create_user(
            "bob",
            auth.DEMO_USER_DEFAULTS["bob"]["password"],
        )
    except Exception:
        pass
    token = auth.create_access_token({"sub": "bob"}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


def _create_project(client: TestClient, hdrs: dict) -> str:
    resp = client.post(
        "/projects",
        json={"name": "Backlog Test Project", "doc_type": "Policy", "phase": "Draft"},
        headers=hdrs,
    )
    assert resp.status_code in (200, 201)
    return resp.json()["id"]


def _create_document(project_id: str) -> str:
    """Insert a document directly via the in-memory store (no HTTP upload needed)."""
    import uuid

    from docreview360.documents import documents as _docs
    from docreview360.documents._models import DocumentModel

    doc_id = str(uuid.uuid4())
    _docs[doc_id] = DocumentModel(
        id=doc_id,
        content="<p>Hello <strong>world</strong></p>",
        project=project_id,
        user="alice",
    )
    return doc_id


def _create_assignment(
    client: TestClient, hdrs: dict, project_id: str, reviewer: str = "bob"
) -> str:
    resp = client.post(
        f"/projects/{project_id}/assignments",
        json={"reviewer": reviewer},
        headers=hdrs,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# ===========================================================================
# Item 50 Phase 4 — compact document view
# ===========================================================================


class TestCompactDocumentView:
    """GET /documents/{doc_id}/compact — read-only mobile view."""

    def test_compact_returns_200_with_plain_text(self) -> None:
        """Compact endpoint returns plain text stripped of HTML tags."""
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        doc_id = _create_document(pid)

        resp = client.get(f"/documents/{doc_id}/compact", headers=hdrs)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == doc_id
        assert data["project"] == pid
        # HTML tags should be stripped
        assert "<p>" not in data["plain_text"]
        assert "<strong>" not in data["plain_text"]
        assert "Hello" in data["plain_text"]
        assert "world" in data["plain_text"]

    def test_compact_includes_word_count(self) -> None:
        """word_count reflects tokens in the stripped plain text."""
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        doc_id = _create_document(pid)

        resp = client.get(f"/documents/{doc_id}/compact", headers=hdrs)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["word_count"], int)
        assert data["word_count"] >= 2  # "Hello world"

    def test_compact_includes_version_and_frozen(self) -> None:
        """Compact response includes version_number and frozen fields."""
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        doc_id = _create_document(pid)

        resp = client.get(f"/documents/{doc_id}/compact", headers=hdrs)
        assert resp.status_code == 200
        data = resp.json()
        assert "version_number" in data
        assert "frozen" in data
        assert data["frozen"] is False

    def test_compact_404_for_unknown_doc(self) -> None:
        """Returns 404 for a non-existent document id."""
        client = TestClient(app)
        hdrs = _alice_headers()
        resp = client.get("/documents/nonexistent-doc-xyz/compact", headers=hdrs)
        assert resp.status_code == 404

    def test_compact_requires_auth(self) -> None:
        """Unauthenticated requests are rejected."""
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        doc_id = _create_document(pid)

        resp = client.get(f"/documents/{doc_id}/compact")
        assert resp.status_code in (401, 403)

    def test_compact_omits_history_and_yjs(self) -> None:
        """Compact response does NOT include history or yjs fields."""
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        doc_id = _create_document(pid)

        resp = client.get(f"/documents/{doc_id}/compact", headers=hdrs)
        assert resp.status_code == 200
        data = resp.json()
        assert "history" not in data
        assert "yjs_updates" not in data
        assert "content" not in data  # raw HTML omitted


# ===========================================================================
# Item 51 — reviewer_sign_offs in ReviewSummary
# ===========================================================================


class TestReviewerSignOffsInSummary:
    """reviewer_sign_offs field in GET /projects/{id}/review-summary."""

    def test_review_summary_has_reviewer_sign_offs_field(self) -> None:
        """review-summary always includes the reviewer_sign_offs list."""
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)

        resp = client.get(f"/projects/{pid}/review-summary", headers=hdrs)
        assert resp.status_code == 200
        data = resp.json()
        assert "reviewer_sign_offs" in data
        assert isinstance(data["reviewer_sign_offs"], list)

    def test_reviewer_sign_offs_empty_before_assignments(self) -> None:
        """reviewer_sign_offs is empty when no assignments exist."""
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)

        resp = client.get(f"/projects/{pid}/review-summary", headers=hdrs)
        assert resp.status_code == 200
        assert resp.json()["reviewer_sign_offs"] == []

    def test_reviewer_sign_offs_shows_in_progress_for_active_reviewer(self) -> None:
        """Assigned reviewer with no sign-off yet shows outcome=in_progress."""
        client = TestClient(app)
        hdrs = _alice_headers()
        _bob_headers()  # ensure bob user is seeded
        pid = _create_project(client, hdrs)
        _create_assignment(client, hdrs, pid)

        resp = client.get(f"/projects/{pid}/review-summary", headers=hdrs)
        assert resp.status_code == 200
        sign_offs = resp.json()["reviewer_sign_offs"]
        assert len(sign_offs) == 1
        assert sign_offs[0]["reviewer"] == "bob"
        assert sign_offs[0]["outcome"] == "in_progress"
        assert sign_offs[0]["concurred_at"] is None

    def test_reviewer_sign_offs_shows_concurred_with_timestamp(self) -> None:
        """After concurrence, reviewer_sign_offs shows outcome=concurred + timestamp."""
        client = TestClient(app)
        hdrs = _alice_headers()
        bob_hdrs = _bob_headers()
        pid = _create_project(client, hdrs)
        aid = _create_assignment(client, hdrs, pid)

        # Bob concurs
        resp = client.post(f"/projects/{pid}/assignments/{aid}/concur", headers=bob_hdrs)
        assert resp.status_code == 200

        resp = client.get(f"/projects/{pid}/review-summary", headers=hdrs)
        assert resp.status_code == 200
        sign_offs = resp.json()["reviewer_sign_offs"]
        concurred = [s for s in sign_offs if s["reviewer"] == "bob"]
        assert len(concurred) == 1
        assert concurred[0]["outcome"] == "concurred"
        assert concurred[0]["concurred_at"] is not None

    def test_reviewer_sign_offs_non_concurred(self) -> None:
        """Non-concurrence is reflected in reviewer_sign_offs."""
        client = TestClient(app)
        hdrs = _alice_headers()
        bob_hdrs = _bob_headers()
        pid = _create_project(client, hdrs)
        aid = _create_assignment(client, hdrs, pid)

        # Start review first
        client.post(f"/projects/{pid}/assignments/{aid}/start", headers=bob_hdrs)
        # Non-concur
        resp = client.post(
            f"/projects/{pid}/assignments/{aid}/non-concur",
            json={"reason": "Policy conflicts with current guidance"},
            headers=bob_hdrs,
        )
        assert resp.status_code == 200

        resp = client.get(f"/projects/{pid}/review-summary", headers=hdrs)
        assert resp.status_code == 200
        sign_offs = resp.json()["reviewer_sign_offs"]
        nc = [s for s in sign_offs if s["reviewer"] == "bob"]
        assert len(nc) == 1
        assert nc[0]["outcome"] == "non_concurred"


# ===========================================================================
# Item 51 — sign-off-map endpoint
# ===========================================================================


class TestSignOffMap:
    """GET /projects/{id}/sign-off-map."""

    def test_sign_off_map_returns_200(self) -> None:
        """sign-off-map endpoint is reachable and returns expected shape."""
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)

        resp = client.get(f"/projects/{pid}/sign-off-map", headers=hdrs)
        assert resp.status_code == 200
        data = resp.json()
        assert data["project_id"] == pid
        assert "reviewer_sign_offs" in data
        assert "formal_approvals" in data
        assert "formality_note" in data
        assert "review_summary" in data

    def test_sign_off_map_formality_note_explains_distinction(self) -> None:
        """formality_note explains the difference between concurrence and approvals."""
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)

        resp = client.get(f"/projects/{pid}/sign-off-map", headers=hdrs)
        assert resp.status_code == 200
        note = resp.json()["formality_note"]
        assert "concurrence" in note.lower()
        assert "formal" in note.lower() or "signature" in note.lower()

    def test_sign_off_map_lists_reviewer_assignments(self) -> None:
        """reviewer_sign_offs lists the assigned reviewers with their outcomes."""
        client = TestClient(app)
        hdrs = _alice_headers()
        _bob_headers()  # ensure bob user is seeded
        pid = _create_project(client, hdrs)
        aid = _create_assignment(client, hdrs, pid)

        resp = client.get(f"/projects/{pid}/sign-off-map", headers=hdrs)
        assert resp.status_code == 200
        sign_offs = resp.json()["reviewer_sign_offs"]
        bob_entry = next((s for s in sign_offs if s["reviewer"] == "bob"), None)
        assert bob_entry is not None
        assert bob_entry["assignment_id"] == aid
        assert bob_entry["outcome"] == "in_progress"

    def test_sign_off_map_shows_concurred_date(self) -> None:
        """After concurrence, concurred_at is populated in sign-off-map."""
        client = TestClient(app)
        hdrs = _alice_headers()
        bob_hdrs = _bob_headers()
        pid = _create_project(client, hdrs)
        aid = _create_assignment(client, hdrs, pid)

        client.post(f"/projects/{pid}/assignments/{aid}/concur", headers=bob_hdrs)

        resp = client.get(f"/projects/{pid}/sign-off-map", headers=hdrs)
        assert resp.status_code == 200
        bob_entry = next(
            (s for s in resp.json()["reviewer_sign_offs"] if s["reviewer"] == "bob"), None
        )
        assert bob_entry is not None
        assert bob_entry["outcome"] == "concurred"
        assert bob_entry["concurred_at"] is not None

    def test_sign_off_map_404_for_unknown_project(self) -> None:
        """Returns 404 for a non-existent project."""
        client = TestClient(app)
        hdrs = _alice_headers()
        resp = client.get("/projects/no-such-project-xyz/sign-off-map", headers=hdrs)
        assert resp.status_code == 404

    def test_sign_off_map_requires_auth(self) -> None:
        """Unauthenticated requests are rejected."""
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        resp = client.get(f"/projects/{pid}/sign-off-map")
        assert resp.status_code in (401, 403)


# ===========================================================================
# Item 51 — ReviewerSignOff model unit tests
# ===========================================================================


class TestReviewerSignOffModel:
    """Unit tests for the ReviewerSignOff model in concurrence_gate."""

    def test_model_fields(self) -> None:
        """ReviewerSignOff has reviewer, outcome, and concurred_at."""
        from docreview360.concurrence_gate import ReviewerSignOff

        so = ReviewerSignOff(
            reviewer="alice", outcome="concurred", concurred_at="2026-03-25T12:00:00+00:00"
        )
        assert so.reviewer == "alice"
        assert so.outcome == "concurred"
        assert so.concurred_at is not None

    def test_model_optional_concurred_at(self) -> None:
        """concurred_at is optional (None for in-progress)."""
        from docreview360.concurrence_gate import ReviewerSignOff

        so = ReviewerSignOff(reviewer="bob", outcome="in_progress")
        assert so.concurred_at is None

    def test_review_summary_includes_sign_offs_field(self) -> None:
        """ReviewSummary model has reviewer_sign_offs list."""
        from docreview360.concurrence_gate import ReviewSummary

        summary = ReviewSummary(
            total_active=0,
            invited=0,
            reviewing=0,
            feedback_submitted=0,
            concurred=0,
            non_concurred=0,
            signed=0,
            declined=0,
            all_complete=False,
            all_signed=False,
            has_non_concurrence=False,
            lifecycle_step="assign_reviewers",
            feedback_total=0,
            feedback_open=0,
            feedback_addressed=0,
        )
        assert summary.reviewer_sign_offs == []

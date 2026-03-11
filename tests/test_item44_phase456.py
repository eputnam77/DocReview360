# SPDX-License-Identifier: MIT
"""Item 44 Phases 4, 5, 6 — Concurrence gate, sign-off, lifecycle, phase archive, reviewer view.

Run targeted:
    DOCREVIEW360_ENV=dev pytest tests/test_item44_phase456.py -v
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


def _create_project(client: TestClient, hdrs: dict[str, str]) -> str:
    resp = client.post(
        "/projects",
        json={"name": "Phase456 Test", "doc_type": "Policy", "phase": "Draft"},
        headers=hdrs,
    )
    assert resp.status_code in (200, 201)
    return resp.json()["id"]


def _create_assignment(client: TestClient, hdrs: dict, pid: str, reviewer: str = "bob") -> str:
    resp = client.post(
        f"/projects/{pid}/assignments",
        json={"reviewer": reviewer},
        headers=hdrs,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Concurrence gate unit tests — Phase 4
# ---------------------------------------------------------------------------


class TestConcurrenceGate:
    """Unit tests for concurrence_gate.py eligibility logic."""

    def test_eligible_with_no_feedback(self) -> None:
        """No feedback items ⟹ eligible to concur."""
        from docreview360.review_assignments import create_assignment
        from docreview360.concurrence_gate import check_concurrence_eligibility
        a = create_assignment("proj-gate-noitems", "bob")
        result = check_concurrence_eligibility("proj-gate-noitems", a.id)
        assert result.eligible is True
        assert result.open_items == 0
        assert result.unanswered_questions == 0

    def test_not_eligible_with_open_items(self) -> None:
        """Open feedback items block concurrence."""
        from docreview360.review_assignments import create_assignment
        from docreview360.feedback_ledger import create_feedback_item
        from docreview360.concurrence_gate import check_concurrence_eligibility
        a = create_assignment("proj-gate-open", "bob")
        create_feedback_item("proj-gate-open", "bob", "Needs fixing", feedback_type="comment")
        result = check_concurrence_eligibility("proj-gate-open", a.id)
        assert result.eligible is False
        assert result.open_items >= 1
        assert result.reason is not None

    def test_eligible_after_all_items_addressed(self) -> None:
        """All items addressed ⟹ eligible."""
        from docreview360.review_assignments import create_assignment
        from docreview360.feedback_ledger import create_feedback_item, dispose_feedback_item
        from docreview360.concurrence_gate import check_concurrence_eligibility
        a = create_assignment("proj-gate-addressed", "bob")
        item = create_feedback_item(
            "proj-gate-addressed", "bob", "Style nit", feedback_type="comment"
        )
        dispose_feedback_item(item.id, "accepted", disposition_by="alice")
        result = check_concurrence_eligibility("proj-gate-addressed", a.id)
        assert result.eligible is True

    def test_unanswered_question_blocks_concurrence(self) -> None:
        """Question with no SME reply blocks concurrence."""
        from docreview360.review_assignments import create_assignment
        from docreview360.feedback_ledger import create_feedback_item
        from docreview360.concurrence_gate import check_concurrence_eligibility
        a = create_assignment("proj-gate-question", "bob")
        create_feedback_item("proj-gate-question", "bob", "What does this mean?", feedback_type="question")
        result = check_concurrence_eligibility("proj-gate-question", a.id)
        assert result.eligible is False
        assert result.unanswered_questions >= 1

    def test_question_with_sme_reply_is_eligible(self) -> None:
        """Question answered by SME (different reviewer) allows concurrence."""
        from docreview360.review_assignments import create_assignment
        from docreview360.feedback_ledger import create_feedback_item, reply_to_feedback
        from docreview360.concurrence_gate import check_concurrence_eligibility
        a = create_assignment("proj-gate-answered", "bob")
        q = create_feedback_item(
            "proj-gate-answered", "bob", "Question?", feedback_type="question"
        )
        # Alice (SME) replies
        reply_to_feedback(q.id, "alice", "The answer is X.")
        result = check_concurrence_eligibility("proj-gate-answered", a.id)
        # Question is still open status, but has an SME reply → eligible
        assert result.unanswered_questions == 0

    def test_invalid_assignment_raises_key_error(self) -> None:
        from docreview360.concurrence_gate import check_concurrence_eligibility
        with pytest.raises(KeyError):
            check_concurrence_eligibility("proj-x", "no-such-assignment")


# ---------------------------------------------------------------------------
# Eligibility API endpoint — Phase 4
# ---------------------------------------------------------------------------


class TestEligibilityEndpoint:
    """Integration tests for GET /projects/{id}/assignments/{aid}/eligibility."""

    def test_eligibility_returns_eligible_true_when_no_feedback(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        aid = _create_assignment(client, hdrs, pid)
        resp = client.get(f"/projects/{pid}/assignments/{aid}/eligibility", headers=hdrs)
        assert resp.status_code == 200
        data = resp.json()
        assert "eligible" in data
        assert data["eligible"] is True

    def test_eligibility_false_with_open_feedback(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        bob_hdrs = _bob_headers()
        aid = _create_assignment(client, hdrs, pid)
        client.post(
            f"/projects/{pid}/feedback",
            json={"text": "Open item", "feedback_type": "comment"},
            headers=bob_hdrs,
        )
        resp = client.get(f"/projects/{pid}/assignments/{aid}/eligibility", headers=hdrs)
        assert resp.status_code == 200
        assert resp.json()["eligible"] is False

    def test_eligibility_requires_auth(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        aid = _create_assignment(client, hdrs, pid)
        resp = client.get(f"/projects/{pid}/assignments/{aid}/eligibility")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Internal sign-off — Phase 4
# ---------------------------------------------------------------------------


class TestSignInternal:
    """Integration tests for POST /projects/{id}/assignments/{aid}/sign-internal."""

    def test_sign_internal_transitions_to_signed(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        bob_hdrs = _bob_headers()
        pid = _create_project(client, hdrs)
        aid = _create_assignment(client, hdrs, pid)
        resp = client.post(
            f"/projects/{pid}/assignments/{aid}/sign-internal",
            json={"note": "LGTM"},
            headers=bob_hdrs,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "signed"
        assert data["signed_at"] is not None

    def test_sign_internal_with_no_note(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        bob_hdrs = _bob_headers()
        pid = _create_project(client, hdrs)
        aid = _create_assignment(client, hdrs, pid)
        resp = client.post(
            f"/projects/{pid}/assignments/{aid}/sign-internal",
            json={},
            headers=bob_hdrs,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "signed"

    def test_sign_internal_wrong_reviewer_returns_403(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        # Alice creates assignment for bob, but then tries to sign as alice
        aid = _create_assignment(client, hdrs, pid, reviewer="bob")
        resp = client.post(
            f"/projects/{pid}/assignments/{aid}/sign-internal",
            json={},
            headers=hdrs,  # alice, not bob
        )
        assert resp.status_code == 403

    def test_sign_internal_twice_returns_409(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        bob_hdrs = _bob_headers()
        pid = _create_project(client, hdrs)
        aid = _create_assignment(client, hdrs, pid)
        client.post(
            f"/projects/{pid}/assignments/{aid}/sign-internal",
            json={},
            headers=bob_hdrs,
        )
        # Second sign attempt
        resp = client.post(
            f"/projects/{pid}/assignments/{aid}/sign-internal",
            json={},
            headers=bob_hdrs,
        )
        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Auto-start (view) endpoint — Phase 5
# ---------------------------------------------------------------------------


class TestAutoStart:
    """Integration tests for POST /projects/{id}/assignments/view."""

    def test_view_starts_invited_assignment(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        bob_hdrs = _bob_headers()
        pid = _create_project(client, hdrs)
        aid = _create_assignment(client, hdrs, pid, reviewer="bob")
        # Bob opens project → invited ⟹ reviewing
        resp = client.post(f"/projects/{pid}/assignments/view", headers=bob_hdrs)
        assert resp.status_code == 200
        data = resp.json()
        assert aid in data["started"]
        # Verify status changed
        get_resp = client.get(f"/projects/{pid}/assignments", headers=hdrs)
        assignments = get_resp.json()
        bob_assign = next((a for a in assignments if a["id"] == aid), None)
        assert bob_assign is not None
        assert bob_assign["status"] == "reviewing"

    def test_view_is_idempotent(self) -> None:
        """Second call should not start again."""
        client = TestClient(app)
        hdrs = _alice_headers()
        bob_hdrs = _bob_headers()
        pid = _create_project(client, hdrs)
        _create_assignment(client, hdrs, pid, reviewer="bob")
        client.post(f"/projects/{pid}/assignments/view", headers=bob_hdrs)
        # Second call
        resp2 = client.post(f"/projects/{pid}/assignments/view", headers=bob_hdrs)
        assert resp2.status_code == 200
        assert resp2.json()["started"] == []

    def test_view_does_not_affect_other_reviewers(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        bob_hdrs = _bob_headers()
        pid = _create_project(client, hdrs)
        aid = _create_assignment(client, hdrs, pid, reviewer="bob")
        # Alice views (not a reviewer) → no changes
        resp = client.post(f"/projects/{pid}/assignments/view", headers=hdrs)
        assert resp.status_code == 200
        assert resp.json()["started"] == []
        # bob's assignment still invited
        get_resp = client.get(f"/projects/{pid}/assignments", headers=hdrs)
        bob_assign = next((a for a in get_resp.json() if a["id"] == aid), None)
        assert bob_assign["status"] == "invited"


# ---------------------------------------------------------------------------
# My-assignments endpoint — Phase 5
# ---------------------------------------------------------------------------


class TestMyAssignments:
    """Integration tests for GET /projects/{id}/assignments/me."""

    def test_me_returns_only_own_assignments(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        bob_hdrs = _bob_headers()
        pid = _create_project(client, hdrs)
        _create_assignment(client, hdrs, pid, reviewer="bob")
        resp = client.get(f"/projects/{pid}/assignments/me", headers=bob_hdrs)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert all(a["reviewer"] == "bob" for a in data)

    def test_me_returns_empty_when_not_assigned(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        bob_hdrs = _bob_headers()
        pid = _create_project(client, hdrs)
        # No assignment for bob
        resp = client.get(f"/projects/{pid}/assignments/me", headers=bob_hdrs)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_me_requires_auth(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        resp = client.get(f"/projects/{pid}/assignments/me")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Review summary endpoint — Phase 6
# ---------------------------------------------------------------------------


class TestReviewSummary:
    """Integration tests for GET /projects/{id}/review-summary."""

    def test_review_summary_no_assignments(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        resp = client.get(f"/projects/{pid}/review-summary", headers=hdrs)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_active"] == 0
        assert data["lifecycle_step"] == "assign_reviewers"

    def test_review_summary_with_reviewer(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        _create_assignment(client, hdrs, pid)
        resp = client.get(f"/projects/{pid}/review-summary", headers=hdrs)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_active"] == 1
        assert data["lifecycle_step"] in (
            "assign_reviewers", "collect_feedback", "address_feedback",
            "collect_signatures", "complete",
        )

    def test_review_summary_all_complete_after_concurrence(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        bob_hdrs = _bob_headers()
        pid = _create_project(client, hdrs)
        aid = _create_assignment(client, hdrs, pid)
        client.post(f"/projects/{pid}/assignments/{aid}/concur", headers=bob_hdrs)
        resp = client.get(f"/projects/{pid}/review-summary", headers=hdrs)
        assert resp.status_code == 200
        data = resp.json()
        assert data["all_complete"] is True
        assert data["lifecycle_step"] in ("collect_signatures", "complete")

    def test_review_summary_has_required_fields(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        resp = client.get(f"/projects/{pid}/review-summary", headers=hdrs)
        assert resp.status_code == 200
        data = resp.json()
        required = [
            "total_active", "invited", "reviewing", "feedback_submitted",
            "concurred", "signed", "all_complete", "all_signed",
            "lifecycle_step", "feedback_total", "feedback_open", "feedback_addressed",
        ]
        for field in required:
            assert field in data, f"Missing field: {field}"

    def test_review_summary_requires_auth(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        resp = client.get(f"/projects/{pid}/review-summary")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Lifecycle step computation — Phase 6 unit tests
# ---------------------------------------------------------------------------


class TestLifecycleStep:
    """Unit tests for _compute_lifecycle_step in concurrence_gate."""

    def _make_assignment(self, status: str):
        from unittest.mock import MagicMock
        a = MagicMock()
        a.status = status
        return a

    def test_no_assignments_returns_assign_reviewers(self) -> None:
        from docreview360.concurrence_gate import _compute_lifecycle_step
        assert _compute_lifecycle_step([], 0, 0) == "assign_reviewers"

    def test_invited_reviewer_collect_feedback(self) -> None:
        from docreview360.concurrence_gate import _compute_lifecycle_step
        assignments = [self._make_assignment("invited")]
        assert _compute_lifecycle_step(assignments, 0, 0) == "collect_feedback"

    def test_all_addressed_feedback_collect_signatures(self) -> None:
        from docreview360.concurrence_gate import _compute_lifecycle_step
        assignments = [self._make_assignment("reviewing")]
        assert _compute_lifecycle_step(assignments, 5, 0) == "collect_signatures"

    def test_open_feedback_address_feedback(self) -> None:
        from docreview360.concurrence_gate import _compute_lifecycle_step
        assignments = [self._make_assignment("reviewing")]
        assert _compute_lifecycle_step(assignments, 5, 2) == "address_feedback"

    def test_all_concurred_complete(self) -> None:
        from docreview360.concurrence_gate import _compute_lifecycle_step
        assignments = [self._make_assignment("concurred"), self._make_assignment("signed")]
        assert _compute_lifecycle_step(assignments, 3, 0) == "complete"


# ---------------------------------------------------------------------------
# Phase feedback archive — Phase 3 (remaining)
# ---------------------------------------------------------------------------


class TestFeedbackPhaseArchive:
    """Tests for GET /feedback/phases and POST /feedback/archive-phase."""

    def test_get_phases_empty(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        resp = client.get(f"/projects/{pid}/feedback/phases", headers=hdrs)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_phases_returns_distinct_phases(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        client.post(
            f"/projects/{pid}/feedback",
            json={"text": "Item 1", "feedback_type": "comment", "phase": "Draft"},
            headers=hdrs,
        )
        client.post(
            f"/projects/{pid}/feedback",
            json={"text": "Item 2", "feedback_type": "comment", "phase": "Review"},
            headers=hdrs,
        )
        client.post(
            f"/projects/{pid}/feedback",
            json={"text": "Item 3", "feedback_type": "comment", "phase": "Draft"},
            headers=hdrs,
        )
        resp = client.get(f"/projects/{pid}/feedback/phases", headers=hdrs)
        phases = resp.json()
        assert "Draft" in phases
        assert "Review" in phases
        # Should not duplicate
        assert len(phases) == len(set(phases))

    def test_archive_phase_resolves_open_items(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        # Add two open items in Draft phase
        client.post(
            f"/projects/{pid}/feedback",
            json={"text": "Open item 1", "feedback_type": "comment", "phase": "Draft"},
            headers=hdrs,
        )
        client.post(
            f"/projects/{pid}/feedback",
            json={"text": "Open item 2", "feedback_type": "suggestion", "phase": "Draft"},
            headers=hdrs,
        )
        resp = client.post(
            f"/projects/{pid}/feedback/archive-phase",
            json={"phase": "Draft"},
            headers=hdrs,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["archived"] == 2
        assert data["phase"] == "Draft"
        # Items should now be resolved
        items_resp = client.get(
            f"/projects/{pid}/feedback?phase=Draft&status=open", headers=hdrs
        )
        assert items_resp.json() == []

    def test_archive_phase_leaves_already_resolved_items(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        create_resp = client.post(
            f"/projects/{pid}/feedback",
            json={"text": "Item", "feedback_type": "comment", "phase": "Draft"},
            headers=hdrs,
        )
        item_id = create_resp.json()["id"]
        # Manually accept first
        client.put(
            f"/projects/{pid}/feedback/{item_id}/disposition",
            json={"status": "accepted"},
            headers=hdrs,
        )
        # Archive should count 0 newly archived
        resp = client.post(
            f"/projects/{pid}/feedback/archive-phase",
            json={"phase": "Draft"},
            headers=hdrs,
        )
        assert resp.status_code == 200
        assert resp.json()["archived"] == 0

    def test_archive_phase_requires_manage_access(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        bob_hdrs = _bob_headers()
        pid = _create_project(client, hdrs)
        resp = client.post(
            f"/projects/{pid}/feedback/archive-phase",
            json={"phase": "Draft"},
            headers=bob_hdrs,
        )
        assert resp.status_code in (403, 404)

    def test_phases_requires_auth(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        resp = client.get(f"/projects/{pid}/feedback/phases")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Review summary unit tests via concurrence_gate module
# ---------------------------------------------------------------------------


class TestGetReviewSummary:
    """Unit tests for get_review_summary()."""

    def test_summary_empty_project(self) -> None:
        from docreview360.concurrence_gate import get_review_summary
        summary = get_review_summary("proj-summary-empty")
        assert summary.total_active == 0
        assert summary.lifecycle_step == "assign_reviewers"
        assert summary.all_complete is False

    def test_summary_with_assignments(self) -> None:
        from docreview360.review_assignments import create_assignment
        from docreview360.concurrence_gate import get_review_summary
        create_assignment("proj-summary-active", "bob")
        create_assignment("proj-summary-active", "alice")
        summary = get_review_summary("proj-summary-active")
        assert summary.total_active == 2
        assert summary.invited == 2

    def test_summary_has_non_concurrence_flag(self) -> None:
        from docreview360.review_assignments import create_assignment, _update_fields
        from docreview360.concurrence_gate import get_review_summary
        a = create_assignment("proj-summary-nonconcur", "bob")
        _update_fields(a.id, status="non_concurred", replacement_reason="Disagree")
        summary = get_review_summary("proj-summary-nonconcur")
        assert summary.has_non_concurrence is True
        assert summary.non_concurred == 1


# ---------------------------------------------------------------------------
# Concur-with-comments endpoint — Phase 4
# ---------------------------------------------------------------------------


class TestConcurWithComments:
    """Integration tests for POST /projects/{id}/assignments/{aid}/concur-with-comments."""

    def test_concur_with_comments_transitions_to_concurred(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        bob_hdrs = _bob_headers()
        pid = _create_project(client, hdrs)
        aid = _create_assignment(client, hdrs, pid)
        resp = client.post(
            f"/projects/{pid}/assignments/{aid}/concur-with-comments",
            json={"text": "Agree overall, but please address the acronym list."},
            headers=bob_hdrs,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "concurred"
        assert data["signed_at"] is not None

    def test_concur_with_comments_creates_feedback_item(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        bob_hdrs = _bob_headers()
        pid = _create_project(client, hdrs)
        aid = _create_assignment(client, hdrs, pid)
        text = "Final note: the acronym list needs updating."
        client.post(
            f"/projects/{pid}/assignments/{aid}/concur-with-comments",
            json={"text": text},
            headers=bob_hdrs,
        )
        # Feedback item should have been created
        feedback_resp = client.get(f"/projects/{pid}/feedback", headers=hdrs)
        items = feedback_resp.json()
        assert any(i["text"] == text and i["reviewer"] == "bob" for i in items)

    def test_concur_with_comments_wrong_reviewer_403(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        aid = _create_assignment(client, hdrs, pid, reviewer="bob")
        # Alice tries to concur bob's assignment
        resp = client.post(
            f"/projects/{pid}/assignments/{aid}/concur-with-comments",
            json={"text": "Not mine to concur"},
            headers=hdrs,
        )
        assert resp.status_code == 403

    def test_concur_with_comments_requires_text(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        bob_hdrs = _bob_headers()
        pid = _create_project(client, hdrs)
        aid = _create_assignment(client, hdrs, pid)
        # Missing text field
        resp = client.post(
            f"/projects/{pid}/assignments/{aid}/concur-with-comments",
            json={},
            headers=bob_hdrs,
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Request concurrence endpoint — Phase 2 (review.concurrence_requested)
# ---------------------------------------------------------------------------


class TestRequestConcurrence:
    """Integration tests for POST /projects/{id}/assignments/{aid}/request-concurrence."""

    def test_request_concurrence_returns_ok(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        aid = _create_assignment(client, hdrs, pid)
        resp = client.post(
            f"/projects/{pid}/assignments/{aid}/request-concurrence",
            headers=hdrs,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["assignment_id"] == aid

    def test_request_concurrence_requires_manage_access(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        bob_hdrs = _bob_headers()
        pid = _create_project(client, hdrs)
        aid = _create_assignment(client, hdrs, pid)
        # Bob is not the project manager
        resp = client.post(
            f"/projects/{pid}/assignments/{aid}/request-concurrence",
            headers=bob_hdrs,
        )
        assert resp.status_code in (403, 404)

    def test_request_concurrence_on_terminal_returns_409(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        bob_hdrs = _bob_headers()
        pid = _create_project(client, hdrs)
        aid = _create_assignment(client, hdrs, pid)
        # Sign the assignment first (terminal)
        client.post(
            f"/projects/{pid}/assignments/{aid}/sign-internal",
            json={},
            headers=bob_hdrs,
        )
        # Request concurrence on a signed (terminal) assignment
        resp = client.post(
            f"/projects/{pid}/assignments/{aid}/request-concurrence",
            headers=hdrs,
        )
        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Phase auto-archive via _update_workflow_phase — Phase 3 (deferred)
# ---------------------------------------------------------------------------


class TestPhaseAutoArchive:
    """Unit test for _update_workflow_phase auto-archiving open feedback."""

    def test_auto_archive_calls_archive_on_phase_change(self) -> None:
        from unittest.mock import MagicMock, patch
        from docreview360.api.projects_router import _update_workflow_phase

        mock_request = MagicMock()
        mock_request.headers = {"content-type": "application/json"}

        mock_body = MagicMock()
        mock_body.phase = "Review"

        mock_project = MagicMock()
        mock_project.workflow = "wf-auto-test"

        mock_wf = MagicMock()
        mock_wf.phase = "Draft"
        mock_wf.phases = ["Draft"]

        with (
            patch("docreview360.workflows.get_workflow", return_value=mock_wf),
            patch("docreview360.feedback_ledger.archive_phase_feedback") as mock_archive,
        ):
            _update_workflow_phase(
                mock_request, mock_body, mock_project,
                project_id="proj-auto-arc", archived_by="alice",
            )
            mock_archive.assert_called_once_with("proj-auto-arc", "Draft", archived_by="alice")

    def test_auto_archive_skipped_when_same_phase(self) -> None:
        from unittest.mock import MagicMock, patch
        from docreview360.api.projects_router import _update_workflow_phase

        mock_request = MagicMock()
        mock_request.headers = {"content-type": "application/json"}

        mock_body = MagicMock()
        mock_body.phase = "Draft"  # same as current

        mock_project = MagicMock()
        mock_project.workflow = "wf-same-phase"

        mock_wf = MagicMock()
        mock_wf.phase = "Draft"
        mock_wf.phases = ["Draft"]

        with (
            patch("docreview360.workflows.get_workflow", return_value=mock_wf),
            patch("docreview360.feedback_ledger.archive_phase_feedback") as mock_archive,
        ):
            _update_workflow_phase(
                mock_request, mock_body, mock_project,
                project_id="proj-same", archived_by="alice",
            )
            mock_archive.assert_not_called()

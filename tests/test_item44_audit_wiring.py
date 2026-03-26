# SPDX-License-Identifier: MIT
"""Item 44 — Audit log + webhook wiring for review lifecycle events.

Verifies that log_event() and emit_lifecycle_event() are called correctly for:
- Creating an assignment           → review.assigned (log + webhook)
- Submitting an assignment         → review.submitted (log + webhook)
- Concurring on an assignment      → review.completed (log + webhook)
- Creating a feedback item         → feedback.submitted (log + webhook)
- Dispositioning a feedback item   → feedback.dispositioned (log)

Run targeted:
    DOCREVIEW360_ENV=dev pytest tests/test_item44_audit_wiring.py -v
"""
from __future__ import annotations

import os
from datetime import timedelta
from unittest.mock import patch

os.environ.setdefault("DOCREVIEW360_ENV", "dev")

from docreview360 import auth
from docreview360.api import app
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

client = TestClient(app, raise_server_exceptions=True)


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


def _create_project(hdrs: dict[str, str]) -> str:
    resp = client.post(
        "/projects",
        json={"name": "Audit Wire Test", "doc_type": "Advisory Circular", "phase": "Draft"},
        headers=hdrs,
    )
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["id"]


def _create_assignment(project_id: str, hdrs: dict[str, str], reviewer: str = "bob") -> str:
    resp = client.post(
        f"/projects/{project_id}/assignments",
        json={"reviewer": reviewer},
        headers=hdrs,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Task 1: log_event() wiring — assignments
# ---------------------------------------------------------------------------


class TestAssignmentAuditLog:
    """Verify log_event() is called for assignment lifecycle state changes."""

    def test_create_assignment_calls_log_event(self) -> None:
        alice = _alice_headers()
        project_id = _create_project(alice)
        with patch("docreview360.api.assignments_router.log_event") as mock_log:
            resp = client.post(
                f"/projects/{project_id}/assignments",
                json={"reviewer": "bob"},
                headers=alice,
            )
            assert resp.status_code == 201
            mock_log.assert_called_once()
            args, kwargs = mock_log.call_args
            assert args[0] == "review.assigned"
            assert kwargs.get("entity_id") == project_id
            assert kwargs.get("reviewer") == "bob"

    def test_submit_assignment_calls_log_event(self) -> None:
        alice = _alice_headers()
        bob = _bob_headers()
        project_id = _create_project(alice)
        assignment_id = _create_assignment(project_id, alice, reviewer="bob")

        # Bob must start first (invited → reviewing)
        client.post(
            f"/projects/{project_id}/assignments/{assignment_id}/start",
            headers=bob,
        )

        with patch("docreview360.api.assignments_router.log_event") as mock_log:
            resp = client.post(
                f"/projects/{project_id}/assignments/{assignment_id}/submit",
                headers=bob,
            )
            assert resp.status_code == 200
            mock_log.assert_called_once()
            args, kwargs = mock_log.call_args
            assert args[0] == "review.submitted"
            assert kwargs.get("entity_id") == project_id
            assert kwargs.get("reviewer") == "bob"

    def test_concur_assignment_calls_log_event(self) -> None:
        alice = _alice_headers()
        bob = _bob_headers()
        project_id = _create_project(alice)
        assignment_id = _create_assignment(project_id, alice, reviewer="bob")

        # Advance to feedback_submitted first
        client.post(
            f"/projects/{project_id}/assignments/{assignment_id}/start",
            headers=bob,
        )
        client.post(
            f"/projects/{project_id}/assignments/{assignment_id}/submit",
            headers=bob,
        )

        with patch("docreview360.api.assignments_router.log_event") as mock_log:
            resp = client.post(
                f"/projects/{project_id}/assignments/{assignment_id}/concur",
                headers=bob,
            )
            assert resp.status_code == 200
            mock_log.assert_called_once()
            args, kwargs = mock_log.call_args
            assert args[0] == "review.completed"
            assert kwargs.get("outcome") == "concurred"

    def test_start_assignment_calls_log_event(self) -> None:
        alice = _alice_headers()
        bob = _bob_headers()
        project_id = _create_project(alice)
        assignment_id = _create_assignment(project_id, alice, reviewer="bob")

        with patch("docreview360.api.assignments_router.log_event") as mock_log:
            resp = client.post(
                f"/projects/{project_id}/assignments/{assignment_id}/start",
                headers=bob,
            )
            assert resp.status_code == 200
            mock_log.assert_called_once()
            args, kwargs = mock_log.call_args
            assert args[0] == "review.status_changed"
            assert kwargs.get("new_status") == "reviewing"

    def test_non_concur_assignment_calls_log_event(self) -> None:
        alice = _alice_headers()
        bob = _bob_headers()
        project_id = _create_project(alice)
        assignment_id = _create_assignment(project_id, alice, reviewer="bob")

        # Start reviewing
        client.post(
            f"/projects/{project_id}/assignments/{assignment_id}/start",
            headers=bob,
        )

        with patch("docreview360.api.assignments_router.log_event") as mock_log:
            resp = client.post(
                f"/projects/{project_id}/assignments/{assignment_id}/non-concur",
                json={"reason": "I disagree with section 3."},
                headers=bob,
            )
            assert resp.status_code == 200
            mock_log.assert_called_once()
            args, kwargs = mock_log.call_args
            assert args[0] == "review.status_changed"
            assert kwargs.get("new_status") == "non_concurred"

    def test_replace_assignment_calls_log_event(self) -> None:
        alice = _alice_headers()
        project_id = _create_project(alice)
        assignment_id = _create_assignment(project_id, alice, reviewer="bob")

        with patch("docreview360.api.assignments_router.log_event") as mock_log:
            resp = client.post(
                f"/projects/{project_id}/assignments/{assignment_id}/replace",
                json={"replacement_reviewer": "alice", "reason": "OOO"},
                headers=alice,
            )
            assert resp.status_code == 200
            mock_log.assert_called_once()
            args, kwargs = mock_log.call_args
            assert args[0] == "review.replaced"
            assert kwargs.get("replacement_reviewer") == "alice"

    def test_delete_assignment_calls_log_event(self) -> None:
        alice = _alice_headers()
        project_id = _create_project(alice)
        assignment_id = _create_assignment(project_id, alice, reviewer="bob")

        with patch("docreview360.api.assignments_router.log_event") as mock_log:
            resp = client.delete(
                f"/projects/{project_id}/assignments/{assignment_id}",
                headers=alice,
            )
            assert resp.status_code == 204
            mock_log.assert_called_once()
            args, kwargs = mock_log.call_args
            assert args[0] == "review.assignment_deleted"
            assert kwargs.get("assignment_id") == assignment_id

    def test_request_concurrence_calls_log_event(self) -> None:
        alice = _alice_headers()
        bob = _bob_headers()
        project_id = _create_project(alice)
        assignment_id = _create_assignment(project_id, alice, reviewer="bob")

        # Put bob in reviewing status so request-concurrence is allowed
        client.post(
            f"/projects/{project_id}/assignments/{assignment_id}/start",
            headers=bob,
        )

        with patch("docreview360.api.assignments_router.log_event") as mock_log:
            resp = client.post(
                f"/projects/{project_id}/assignments/{assignment_id}/request-concurrence",
                headers=alice,
            )
            assert resp.status_code == 200
            mock_log.assert_called_once()
            args, kwargs = mock_log.call_args
            assert args[0] == "review.concurrence_requested"

    def test_concur_with_comments_calls_log_event(self) -> None:
        alice = _alice_headers()
        bob = _bob_headers()
        project_id = _create_project(alice)
        assignment_id = _create_assignment(project_id, alice, reviewer="bob")

        client.post(
            f"/projects/{project_id}/assignments/{assignment_id}/start",
            headers=bob,
        )
        client.post(
            f"/projects/{project_id}/assignments/{assignment_id}/submit",
            headers=bob,
        )

        with patch("docreview360.api.assignments_router.log_event") as mock_log:
            resp = client.post(
                f"/projects/{project_id}/assignments/{assignment_id}/concur-with-comments",
                json={"text": "All good, minor notes attached."},
                headers=bob,
            )
            assert resp.status_code == 200
            mock_log.assert_called_once()
            args, kwargs = mock_log.call_args
            assert args[0] == "review.completed"
            assert kwargs.get("outcome") == "concurred_with_comments"


# ---------------------------------------------------------------------------
# Task 1: log_event() wiring — feedback
# ---------------------------------------------------------------------------


class TestFeedbackAuditLog:
    """Verify log_event() is called for feedback lifecycle state changes."""

    def test_create_feedback_calls_log_event(self) -> None:
        alice = _alice_headers()
        project_id = _create_project(alice)

        with patch("docreview360.api.feedback_router.log_event") as mock_log:
            resp = client.post(
                f"/projects/{project_id}/feedback",
                json={"text": "This paragraph is unclear.", "feedback_type": "comment"},
                headers=alice,
            )
            assert resp.status_code == 201
            mock_log.assert_called_once()
            args, kwargs = mock_log.call_args
            assert args[0] == "feedback.submitted"
            assert kwargs.get("entity_id") == project_id
            assert kwargs.get("feedback_type") == "comment"

    def test_disposition_feedback_calls_log_event(self) -> None:
        alice = _alice_headers()
        project_id = _create_project(alice)

        # Create a feedback item first
        resp = client.post(
            f"/projects/{project_id}/feedback",
            json={"text": "Section 2 needs work.", "feedback_type": "suggestion"},
            headers=alice,
        )
        assert resp.status_code == 201
        item_id = resp.json()["id"]

        with patch("docreview360.api.feedback_router.log_event") as mock_log:
            resp = client.put(
                f"/projects/{project_id}/feedback/{item_id}/disposition",
                json={"status": "accepted", "reason": "Valid point."},
                headers=alice,
            )
            assert resp.status_code == 200
            mock_log.assert_called_once()
            args, kwargs = mock_log.call_args
            assert args[0] == "feedback.dispositioned"
            assert kwargs.get("disposition") == "accepted"
            assert kwargs.get("feedback_id") == item_id

    def test_reply_to_feedback_calls_log_event(self) -> None:
        alice = _alice_headers()
        project_id = _create_project(alice)

        resp = client.post(
            f"/projects/{project_id}/feedback",
            json={"text": "Can you clarify?", "feedback_type": "question"},
            headers=alice,
        )
        assert resp.status_code == 201
        item_id = resp.json()["id"]

        with patch("docreview360.api.feedback_router.log_event") as mock_log:
            resp = client.post(
                f"/projects/{project_id}/feedback/{item_id}/reply",
                json={"text": "Yes, clarified in section 2."},
                headers=alice,
            )
            assert resp.status_code == 201
            mock_log.assert_called_once()
            args, kwargs = mock_log.call_args
            assert args[0] == "feedback.replied"
            assert kwargs.get("feedback_id") == item_id

    def test_archive_phase_calls_log_event(self) -> None:
        alice = _alice_headers()
        project_id = _create_project(alice)

        # Create some feedback in phase "Draft"
        client.post(
            f"/projects/{project_id}/feedback",
            json={"text": "Draft feedback item.", "feedback_type": "comment", "phase": "Draft"},
            headers=alice,
        )

        with patch("docreview360.api.feedback_router.log_event") as mock_log:
            resp = client.post(
                f"/projects/{project_id}/feedback/archive-phase",
                json={"phase": "Draft"},
                headers=alice,
            )
            assert resp.status_code == 200
            mock_log.assert_called_once()
            args, kwargs = mock_log.call_args
            assert args[0] == "feedback.phase_archived"
            assert kwargs.get("phase") == "Draft"


# ---------------------------------------------------------------------------
# Task 2: emit_lifecycle_event() webhook wiring
# ---------------------------------------------------------------------------


class TestWebhookLifecycleEvents:
    """Verify emit_lifecycle_event() is called for key review lifecycle events."""

    def test_create_assignment_emits_review_assigned_webhook(self) -> None:
        alice = _alice_headers()
        project_id = _create_project(alice)

        with patch("docreview360.api.assignments_router._emit_webhook") as mock_wh:
            resp = client.post(
                f"/projects/{project_id}/assignments",
                json={"reviewer": "bob"},
                headers=alice,
            )
            assert resp.status_code == 201
            mock_wh.assert_called_once_with(
                "review.assigned",
                {
                    "project_id": project_id,
                    "assignment_id": resp.json()["id"],
                    "reviewer": "bob",
                },
            )

    def test_submit_assignment_emits_review_submitted_webhook(self) -> None:
        alice = _alice_headers()
        bob = _bob_headers()
        project_id = _create_project(alice)
        assignment_id = _create_assignment(project_id, alice, reviewer="bob")

        client.post(
            f"/projects/{project_id}/assignments/{assignment_id}/start",
            headers=bob,
        )

        with patch("docreview360.api.assignments_router._emit_webhook") as mock_wh:
            resp = client.post(
                f"/projects/{project_id}/assignments/{assignment_id}/submit",
                headers=bob,
            )
            assert resp.status_code == 200
            mock_wh.assert_called_once()
            call_event = mock_wh.call_args[0][0]
            call_data = mock_wh.call_args[0][1]
            assert call_event == "review.submitted"
            assert call_data["project_id"] == project_id
            assert call_data["reviewer"] == "bob"

    def test_concur_assignment_emits_review_completed_webhook(self) -> None:
        alice = _alice_headers()
        bob = _bob_headers()
        project_id = _create_project(alice)
        assignment_id = _create_assignment(project_id, alice, reviewer="bob")

        client.post(
            f"/projects/{project_id}/assignments/{assignment_id}/start",
            headers=bob,
        )
        client.post(
            f"/projects/{project_id}/assignments/{assignment_id}/submit",
            headers=bob,
        )

        with patch("docreview360.api.assignments_router._emit_webhook") as mock_wh:
            resp = client.post(
                f"/projects/{project_id}/assignments/{assignment_id}/concur",
                headers=bob,
            )
            assert resp.status_code == 200
            mock_wh.assert_called_once()
            call_event = mock_wh.call_args[0][0]
            call_data = mock_wh.call_args[0][1]
            assert call_event == "review.completed"
            assert call_data["outcome"] == "concurred"

    def test_create_feedback_emits_feedback_submitted_webhook(self) -> None:
        alice = _alice_headers()
        project_id = _create_project(alice)

        with patch("docreview360.api.feedback_router._emit_webhook") as mock_wh:
            resp = client.post(
                f"/projects/{project_id}/feedback",
                json={"text": "Webhook test feedback.", "feedback_type": "comment"},
                headers=alice,
            )
            assert resp.status_code == 201
            mock_wh.assert_called_once()
            call_event = mock_wh.call_args[0][0]
            call_data = mock_wh.call_args[0][1]
            assert call_event == "feedback.submitted"
            assert call_data["project_id"] == project_id
            assert call_data["reviewer"] == "alice"

    def test_sign_internally_emits_review_completed_webhook(self) -> None:
        alice = _alice_headers()
        bob = _bob_headers()
        project_id = _create_project(alice)
        assignment_id = _create_assignment(project_id, alice, reviewer="bob")

        client.post(
            f"/projects/{project_id}/assignments/{assignment_id}/start",
            headers=bob,
        )

        with patch("docreview360.api.assignments_router._emit_webhook") as mock_wh:
            resp = client.post(
                f"/projects/{project_id}/assignments/{assignment_id}/sign-internal",
                json={"note": "Acknowledged"},
                headers=bob,
            )
            assert resp.status_code == 200
            mock_wh.assert_called_once()
            call_event = mock_wh.call_args[0][0]
            call_data = mock_wh.call_args[0][1]
            assert call_event == "review.completed"
            assert call_data["outcome"] == "signed"

    def test_concur_with_comments_emits_review_completed_webhook(self) -> None:
        alice = _alice_headers()
        bob = _bob_headers()
        project_id = _create_project(alice)
        assignment_id = _create_assignment(project_id, alice, reviewer="bob")

        client.post(
            f"/projects/{project_id}/assignments/{assignment_id}/start",
            headers=bob,
        )
        client.post(
            f"/projects/{project_id}/assignments/{assignment_id}/submit",
            headers=bob,
        )

        with patch("docreview360.api.assignments_router._emit_webhook") as mock_wh:
            resp = client.post(
                f"/projects/{project_id}/assignments/{assignment_id}/concur-with-comments",
                json={"text": "All LGTM with minor notes."},
                headers=bob,
            )
            assert resp.status_code == 200
            mock_wh.assert_called_once()
            call_event = mock_wh.call_args[0][0]
            call_data = mock_wh.call_args[0][1]
            assert call_event == "review.completed"
            assert call_data["outcome"] == "concurred_with_comments"

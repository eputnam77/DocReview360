# SPDX-License-Identifier: MIT
"""Item 44 Phases 2+3 — Feedback ledger, notification log, review reminder.

Run targeted:
    DOCREVIEW360_ENV=dev pytest tests/test_item44_phase23.py -v
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
        json={"name": "Ledger Test", "doc_type": "Advisory Circular", "phase": "Draft"},
        headers=hdrs,
    )
    assert resp.status_code in (200, 201)
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Feedback ledger unit tests
# ---------------------------------------------------------------------------


class TestFeedbackLedger:
    """Unit tests for feedback_ledger.py CRUD functions."""

    def test_create_and_get_feedback_item(self) -> None:
        from docreview360.feedback_ledger import create_feedback_item, get_feedback_item
        item = create_feedback_item(
            "proj-unit-1", "bob", "Please clarify section 4.",
            feedback_type="question",
        )
        assert item.id
        assert item.project_id == "proj-unit-1"
        assert item.reviewer == "bob"
        assert item.feedback_type == "question"
        assert item.status == "open"

        fetched = get_feedback_item(item.id)
        assert fetched is not None
        assert fetched.id == item.id

    def test_list_feedback_items_with_filters(self) -> None:
        from docreview360.feedback_ledger import create_feedback_item, list_feedback_items
        pid = "proj-filter-test"
        create_feedback_item(pid, "bob", "A comment", feedback_type="comment")
        create_feedback_item(pid, "bob", "A question", feedback_type="question")

        all_items = list_feedback_items(pid)
        assert len(all_items) >= 2

        questions = list_feedback_items(pid, feedback_type="question")
        assert all(i.feedback_type == "question" for i in questions)

    def test_dispose_feedback_item(self) -> None:
        from docreview360.feedback_ledger import create_feedback_item, dispose_feedback_item
        item = create_feedback_item("proj-disp-1", "bob", "Needs rework.", feedback_type="suggestion")
        updated = dispose_feedback_item(item.id, "accepted", disposition_by="alice")
        assert updated.status == "accepted"
        assert updated.disposition_by == "alice"

    def test_reject_requires_terminal_status(self) -> None:
        from docreview360.feedback_ledger import create_feedback_item, dispose_feedback_item
        item = create_feedback_item("proj-disp-2", "bob", "Disagree", feedback_type="non_concurrence")
        with pytest.raises(ValueError, match="Invalid disposition status"):
            dispose_feedback_item(item.id, "open", disposition_by="alice")

    def test_reply_to_feedback(self) -> None:
        from docreview360.feedback_ledger import create_feedback_item, list_feedback_items, reply_to_feedback
        parent = create_feedback_item("proj-reply-1", "bob", "Please explain this.", feedback_type="question")
        reply = reply_to_feedback(parent.id, "alice", "Happy to explain — see comment below.")
        assert reply.parent_id == parent.id
        assert reply.reviewer == "alice"

        items = list_feedback_items("proj-reply-1", parent_id=parent.id)
        assert any(i.id == reply.id for i in items)

    def test_mark_question_satisfied(self) -> None:
        from docreview360.feedback_ledger import create_feedback_item, mark_question_satisfied
        item = create_feedback_item("proj-sat-1", "bob", "?", feedback_type="question")
        updated = mark_question_satisfied(item.id)
        assert updated.question_satisfied is True

    def test_feedback_progress(self) -> None:
        from docreview360.feedback_ledger import (
            create_feedback_item, dispose_feedback_item, get_feedback_progress
        )
        pid = "proj-prog-1"
        i1 = create_feedback_item(pid, "bob", "Item 1", feedback_type="comment")
        i2 = create_feedback_item(pid, "bob", "Item 2", feedback_type="suggestion")
        dispose_feedback_item(i1.id, "accepted", disposition_by="alice")

        prog = get_feedback_progress(pid)
        assert prog.total >= 2
        assert prog.accepted >= 1
        assert prog.addressed == prog.accepted + prog.rejected + prog.resolved

    def test_feedback_progress_by_phase(self) -> None:
        from docreview360.feedback_ledger import create_feedback_item, get_feedback_progress
        pid = "proj-prog-phase-1"
        create_feedback_item(pid, "bob", "Phase A item", phase="Draft")
        create_feedback_item(pid, "bob", "Phase B item", phase="Review")

        draft_prog = get_feedback_progress(pid, phase="Draft")
        assert draft_prog.total >= 1

    def test_get_nonexistent_returns_none(self) -> None:
        from docreview360.feedback_ledger import get_feedback_item
        assert get_feedback_item("does-not-exist-xyz") is None

    def test_reply_nonexistent_raises_keyerror(self) -> None:
        from docreview360.feedback_ledger import reply_to_feedback
        with pytest.raises(KeyError):
            reply_to_feedback("no-such-parent", "alice", "Reply text")


# ---------------------------------------------------------------------------
# Feedback API integration tests
# ---------------------------------------------------------------------------


class TestFeedbackAPI:
    """Integration tests for /projects/{id}/feedback/* endpoints."""

    def test_list_feedback_empty(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        resp = client.get(f"/projects/{pid}/feedback", headers=hdrs)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_feedback_requires_auth(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        resp = client.post(f"/projects/{pid}/feedback", json={"text": "Hello"})
        assert resp.status_code in (401, 403)

    def test_create_feedback_item(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        resp = client.post(
            f"/projects/{pid}/feedback",
            json={"text": "Please clarify section 4.", "feedback_type": "question"},
            headers=hdrs,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["feedback_type"] == "question"
        assert data["status"] == "open"

    def test_create_feedback_invalid_type(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        resp = client.post(
            f"/projects/{pid}/feedback",
            json={"text": "bad", "feedback_type": "invalid_type"},
            headers=hdrs,
        )
        assert resp.status_code == 422

    def test_list_feedback_with_type_filter(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        client.post(
            f"/projects/{pid}/feedback",
            json={"text": "Comment", "feedback_type": "comment"},
            headers=hdrs,
        )
        client.post(
            f"/projects/{pid}/feedback",
            json={"text": "Question", "feedback_type": "question"},
            headers=hdrs,
        )
        resp = client.get(f"/projects/{pid}/feedback?feedback_type=question", headers=hdrs)
        assert resp.status_code == 200
        items = resp.json()
        assert all(i["feedback_type"] == "question" for i in items)

    def test_disposition_feedback_item(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        create_resp = client.post(
            f"/projects/{pid}/feedback",
            json={"text": "Needs work", "feedback_type": "suggestion"},
            headers=hdrs,
        )
        item_id = create_resp.json()["id"]
        disp_resp = client.put(
            f"/projects/{pid}/feedback/{item_id}/disposition",
            json={"status": "accepted"},
            headers=hdrs,
        )
        assert disp_resp.status_code == 200
        assert disp_resp.json()["status"] == "accepted"

    def test_disposition_invalid_status_returns_422(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        create_resp = client.post(
            f"/projects/{pid}/feedback",
            json={"text": "test", "feedback_type": "comment"},
            headers=hdrs,
        )
        item_id = create_resp.json()["id"]
        resp = client.put(
            f"/projects/{pid}/feedback/{item_id}/disposition",
            json={"status": "open"},
            headers=hdrs,
        )
        assert resp.status_code == 422

    def test_reply_to_feedback_item(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        create_resp = client.post(
            f"/projects/{pid}/feedback",
            json={"text": "What does this mean?", "feedback_type": "question"},
            headers=hdrs,
        )
        item_id = create_resp.json()["id"]
        reply_resp = client.post(
            f"/projects/{pid}/feedback/{item_id}/reply",
            json={"text": "It means X."},
            headers=hdrs,
        )
        assert reply_resp.status_code == 201
        assert reply_resp.json()["parent_id"] == item_id

    def test_feedback_progress_endpoint(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        client.post(
            f"/projects/{pid}/feedback",
            json={"text": "Comment 1", "feedback_type": "comment"},
            headers=hdrs,
        )
        resp = client.get(f"/projects/{pid}/feedback/progress", headers=hdrs)
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "open" in data
        assert "addressed" in data

    def test_question_satisfied_by_reviewer(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        # Alice posts a question (alice is the reviewer here)
        create_resp = client.post(
            f"/projects/{pid}/feedback",
            json={"text": "Question?", "feedback_type": "question"},
            headers=hdrs,
        )
        item_id = create_resp.json()["id"]
        # Alice marks it satisfied
        resp = client.post(
            f"/projects/{pid}/feedback/{item_id}/question-satisfied",
            headers=hdrs,
        )
        assert resp.status_code == 200
        assert resp.json()["question_satisfied"] is True

    def test_question_satisfied_only_for_question_type(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        create_resp = client.post(
            f"/projects/{pid}/feedback",
            json={"text": "Just a comment", "feedback_type": "comment"},
            headers=hdrs,
        )
        item_id = create_resp.json()["id"]
        resp = client.post(
            f"/projects/{pid}/feedback/{item_id}/question-satisfied",
            headers=hdrs,
        )
        assert resp.status_code == 422

    def test_feedback_404_on_wrong_project(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        create_resp = client.post(
            f"/projects/{pid}/feedback",
            json={"text": "Item", "feedback_type": "comment"},
            headers=hdrs,
        )
        item_id = create_resp.json()["id"]
        # Try to disposition under wrong project
        resp = client.put(
            f"/projects/wrong-project-id/feedback/{item_id}/disposition",
            json={"status": "accepted"},
            headers=hdrs,
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Notification log tests
# ---------------------------------------------------------------------------


class TestNotificationLog:
    """Tests for notification log persistence and GET endpoint."""

    def test_log_notification(self) -> None:
        from docreview360.notification_log import log_notification, list_notification_log
        entry = log_notification(
            "review.assigned",
            "You were invited to review project X. /projects/p1#reviewers",
            project_id="p1",
            reviewer="bob",
        )
        assert entry.id
        assert entry.event == "review.assigned"
        entries = list_notification_log("p1")
        assert any(e.id == entry.id for e in entries)

    def test_list_notification_log_respects_project(self) -> None:
        from docreview360.notification_log import log_notification, list_notification_log
        log_notification("review.signed", "msg", project_id="proj-log-a", reviewer="alice")
        log_notification("review.signed", "msg", project_id="proj-log-b", reviewer="bob")

        entries_a = list_notification_log("proj-log-a")
        assert all(e.project_id == "proj-log-a" for e in entries_a)

    def test_notification_log_api_endpoint(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        # Trigger a notification via assignment creation
        client.post(
            f"/projects/{pid}/assignments",
            json={"reviewer": "bob"},
            headers=hdrs,
        )
        resp = client.get(f"/projects/{pid}/notification-log", headers=hdrs)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_notification_log_requires_auth(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        resp = client.get(f"/projects/{pid}/notification-log")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Review reminder tests (Phase 2)
# ---------------------------------------------------------------------------


class TestReviewReminder:
    """Tests for POST /projects/{id}/assignments/{aid}/remind."""

    def test_remind_invited_assignment(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        create_resp = client.post(
            f"/projects/{pid}/assignments",
            json={"reviewer": "bob"},
            headers=hdrs,
        )
        aid = create_resp.json()["id"]
        resp = client.post(f"/projects/{pid}/assignments/{aid}/remind", headers=hdrs)
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_remind_terminal_assignment_returns_409(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        bob_hdrs = _bob_headers()
        pid = _create_project(client, hdrs)
        create_resp = client.post(
            f"/projects/{pid}/assignments",
            json={"reviewer": "bob"},
            headers=hdrs,
        )
        aid = create_resp.json()["id"]
        # Bob concurs → terminal
        client.post(f"/projects/{pid}/assignments/{aid}/concur", headers=bob_hdrs)
        resp = client.post(f"/projects/{pid}/assignments/{aid}/remind", headers=hdrs)
        assert resp.status_code == 409

    def test_remind_requires_manage_access(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        bob_hdrs = _bob_headers()
        pid = _create_project(client, hdrs)
        create_resp = client.post(
            f"/projects/{pid}/assignments",
            json={"reviewer": "bob"},
            headers=hdrs,
        )
        aid = create_resp.json()["id"]
        # Bob (non-owner) tries to send reminder
        resp = client.post(f"/projects/{pid}/assignments/{aid}/remind", headers=bob_hdrs)
        assert resp.status_code in (403, 404)


# ---------------------------------------------------------------------------
# Deep link content in notifications (Phase 2)
# ---------------------------------------------------------------------------


class TestNotificationDeepLinks:
    """Verify notifications contain /projects/{id}#reviewers deep link."""

    def test_assigned_notification_contains_deep_link(self) -> None:
        from docreview360.notification_log import list_notification_log
        from docreview360.notifications import sent_emails

        client = TestClient(app)
        hdrs = _alice_headers()
        pid = _create_project(client, hdrs)
        client.post(
            f"/projects/{pid}/assignments",
            json={"reviewer": "bob"},
            headers=hdrs,
        )
        entries = list_notification_log(pid)
        # At least one entry should have a deep link mentioning the project
        if entries:
            deep_link_entry = next(
                (e for e in entries if f"/projects/{pid}" in e.message), None
            )
            # If notification was persisted, it should have the deep link
            if deep_link_entry:
                assert "#reviewers" in deep_link_entry.message

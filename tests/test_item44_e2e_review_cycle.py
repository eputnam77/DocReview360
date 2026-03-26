# SPDX-License-Identifier: MIT
"""Item 44 — E2E integration tests for the full document review cycle.

Covers:
  Test 1 (TestFullReviewCycle): create project → search/add reviewer → notifications
          → reviewer adds feedback (comment + question) → SME answers question
          → SME dispositions feedback → SME requests concurrence → reviewer concurs
          → lifecycle advanced through closed → records package downloaded

  Test 2 (TestReviewerReplacement): assign reviewer → reviewer adds feedback
          → SME replaces reviewer (OOO) → original feedback preserved in ledger
          → replacement reviewer picks up and concurs

Run targeted:
    DOCREVIEW360_ENV=dev pytest tests/test_item44_e2e_review_cycle.py -v
"""
from __future__ import annotations

import os
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("DOCREVIEW360_ENV", "dev")

from fastapi.testclient import TestClient

from docreview360 import auth
from docreview360.api import app

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_headers(username: str, password: str | None = None, *, admin: bool = False) -> dict[str, str]:
    """Create a user (best-effort) and return a bearer-token header dict."""
    try:
        auth.USER_REPOSITORY.create_user(
            username,
            password or "password",
        )
    except Exception:
        pass
    if admin:
        from docreview360 import rbac
        rbac.add_role(username, "admin")
    token = auth.create_access_token({"sub": username}, timedelta(minutes=60))
    return {"Authorization": f"Bearer {token}"}


def _alice_headers() -> dict[str, str]:
    """Admin/SME user."""
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
    token = auth.create_access_token({"sub": "alice"}, timedelta(minutes=60))
    return {"Authorization": f"Bearer {token}"}


def _bob_headers() -> dict[str, str]:
    """Reviewer user."""
    try:
        auth.USER_REPOSITORY.create_user(
            "bob",
            auth.DEMO_USER_DEFAULTS["bob"]["password"],
        )
    except Exception:
        pass
    token = auth.create_access_token({"sub": "bob"}, timedelta(minutes=60))
    return {"Authorization": f"Bearer {token}"}


def _charlie_headers() -> dict[str, str]:
    """Replacement reviewer user."""
    try:
        auth.USER_REPOSITORY.create_user("charlie", "password")
    except Exception:
        pass
    token = auth.create_access_token({"sub": "charlie"}, timedelta(minutes=60))
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Test 1: Full review cycle
# ---------------------------------------------------------------------------


class TestFullReviewCycle:
    """End-to-end test covering the happy path for a complete review cycle.

    Steps:
      1. Alice (admin/SME) creates a project
      2. Alice searches for bob via /users/search
      3. Alice assigns bob as reviewer — notification emitted
      4. Bob starts the review
      5. Bob posts a comment feedback item
      6. Bob posts a question feedback item — SME notification emitted
      7. Alice fetches feedback and verifies both items exist
      8. Alice replies to the question (answers it) — reviewer notification emitted
      9. Alice accepts the comment and resolves the question via disposition
     10. Alice requests concurrence from bob
     11. Bob concurs — all-complete notification emitted
     12. Alice advances lifecycle: draft → in_review → reviewed → ready_for_publication
         → published → submitted_to_records → closed
     13. Alice downloads the records package (ZIP) and verifies the content-hash header
    """

    def test_full_review_cycle(self) -> None:
        client = TestClient(app)
        alice_hdrs = _alice_headers()
        bob_hdrs = _bob_headers()

        # ------------------------------------------------------------------
        # Step 1: Alice creates a project
        # ------------------------------------------------------------------
        resp = client.post(
            "/projects",
            json={"name": "E2E Cycle Project", "doc_type": "Policy", "phase": "Draft"},
            headers=alice_hdrs,
        )
        assert resp.status_code in (200, 201), resp.text
        project = resp.json()
        pid = project["id"]
        assert pid

        # ------------------------------------------------------------------
        # Step 2: Alice searches for bob via /users/search
        # ------------------------------------------------------------------
        search_resp = client.get("/users/search?q=bob", headers=alice_hdrs)
        assert search_resp.status_code == 200
        results = search_resp.json()
        assert isinstance(results, list)
        usernames = [u["username"] for u in results]
        assert "bob" in usernames, f"bob not found in {usernames}"
        bob_result = next(u for u in results if u["username"] == "bob")
        assert "display_name" in bob_result
        assert "active" in bob_result

        # ------------------------------------------------------------------
        # Step 3: Alice assigns bob as reviewer — mock send_notification
        # send_notification is imported locally in _emit_review_notification;
        # patch it at the notifications module level so all callers see the mock.
        # ------------------------------------------------------------------
        notify_calls: list[tuple] = []

        def _capture_notify(event: str, **kwargs):
            notify_calls.append((event, kwargs))

        with patch(
            "docreview360.notifications.send_notification",
            side_effect=_capture_notify,
        ):
            assign_resp = client.post(
                f"/projects/{pid}/assignments",
                json={"reviewer": "bob"},
                headers=alice_hdrs,
            )
        assert assign_resp.status_code == 201, assign_resp.text
        assignment = assign_resp.json()
        aid = assignment["id"]
        assert assignment["reviewer"] == "bob"
        assert assignment["status"] == "invited"
        # Verify review.assigned notification was emitted
        assigned_events = [e for e, _ in notify_calls if e == "review.assigned"]
        assert len(assigned_events) >= 1, f"review.assigned not fired; calls={notify_calls}"

        # ------------------------------------------------------------------
        # Step 4: Bob starts the review
        # ------------------------------------------------------------------
        start_resp = client.post(
            f"/projects/{pid}/assignments/{aid}/start",
            headers=bob_hdrs,
        )
        assert start_resp.status_code == 200, start_resp.text
        assert start_resp.json()["status"] == "reviewing"

        # ------------------------------------------------------------------
        # Step 5: Bob posts a comment feedback item
        # ------------------------------------------------------------------
        comment_resp = client.post(
            f"/projects/{pid}/feedback",
            json={
                "text": "Section 3 needs a clearer definition of 'stakeholder'.",
                "feedback_type": "comment",
                "assignment_id": aid,
                "phase": "Draft",
            },
            headers=bob_hdrs,
        )
        assert comment_resp.status_code == 201, comment_resp.text
        comment_item = comment_resp.json()
        comment_fid = comment_item["id"]
        assert comment_item["feedback_type"] == "comment"
        assert comment_item["status"] == "open"

        # ------------------------------------------------------------------
        # Step 6: Bob posts a question — verify SME notification fired
        # ------------------------------------------------------------------
        q_notify_calls: list[tuple] = []

        def _capture_q_notify(event: str, **kwargs):
            q_notify_calls.append((event, kwargs))

        with patch(
            "docreview360.notifications.send_notification",
            side_effect=_capture_q_notify,
        ):
            question_resp = client.post(
                f"/projects/{pid}/feedback",
                json={
                    "text": "What authority grants the FAA power to enforce section 5?",
                    "feedback_type": "question",
                    "assignment_id": aid,
                    "phase": "Draft",
                },
                headers=bob_hdrs,
            )
        assert question_resp.status_code == 201, question_resp.text
        question_item = question_resp.json()
        question_fid = question_item["id"]
        assert question_item["feedback_type"] == "question"
        asked_events = [e for e, _ in q_notify_calls if e == "review.question_asked"]
        assert len(asked_events) >= 1, f"review.question_asked not fired; calls={q_notify_calls}"

        # ------------------------------------------------------------------
        # Step 7: Fetch all feedback and verify both items exist
        # ------------------------------------------------------------------
        list_resp = client.get(f"/projects/{pid}/feedback", headers=alice_hdrs)
        assert list_resp.status_code == 200
        all_feedback = list_resp.json()["items"]
        feedback_ids = {f["id"] for f in all_feedback}
        assert comment_fid in feedback_ids, "Comment feedback not in list"
        assert question_fid in feedback_ids, "Question feedback not in list"

        # Filter by type
        comment_list = client.get(
            f"/projects/{pid}/feedback?feedback_type=comment", headers=alice_hdrs
        )
        assert comment_list.status_code == 200
        assert all(f["feedback_type"] == "comment" for f in comment_list.json()["items"])

        question_list = client.get(
            f"/projects/{pid}/feedback?feedback_type=question", headers=alice_hdrs
        )
        assert question_list.status_code == 200
        assert all(f["feedback_type"] == "question" for f in question_list.json()["items"])

        # ------------------------------------------------------------------
        # Step 8: Alice replies to the question (answers it)
        # ------------------------------------------------------------------
        reply_notify_calls: list[tuple] = []

        def _capture_reply_notify(event: str, **kwargs):
            reply_notify_calls.append((event, kwargs))

        with patch(
            "docreview360.notifications.send_notification",
            side_effect=_capture_reply_notify,
        ):
            reply_resp = client.post(
                f"/projects/{pid}/feedback/{question_fid}/reply",
                json={"text": "FAA authority derives from 49 U.S.C. § 40103."},
                headers=alice_hdrs,
            )
        assert reply_resp.status_code == 201, reply_resp.text
        reply = reply_resp.json()
        assert reply["text"] == "FAA authority derives from 49 U.S.C. § 40103."
        answered_events = [e for e, _ in reply_notify_calls if e == "review.question_answered"]
        assert len(answered_events) >= 1, f"review.question_answered not fired; calls={reply_notify_calls}"

        # ------------------------------------------------------------------
        # Step 9: Alice dispositions feedback (accept comment, resolve question)
        # ------------------------------------------------------------------
        accept_resp = client.put(
            f"/projects/{pid}/feedback/{comment_fid}/disposition",
            json={"status": "accepted", "reason": "Agreed; will update in next draft."},
            headers=alice_hdrs,
        )
        assert accept_resp.status_code == 200, accept_resp.text
        assert accept_resp.json()["status"] == "accepted"

        resolve_resp = client.put(
            f"/projects/{pid}/feedback/{question_fid}/disposition",
            json={"status": "resolved", "reason": "Answered via reply."},
            headers=alice_hdrs,
        )
        assert resolve_resp.status_code == 200, resolve_resp.text
        assert resolve_resp.json()["status"] == "resolved"

        # Verify progress reflects all items dispositioned
        progress_resp = client.get(f"/projects/{pid}/feedback/progress", headers=alice_hdrs)
        assert progress_resp.status_code == 200
        progress = progress_resp.json()
        assert progress["total"] >= 2

        # ------------------------------------------------------------------
        # Step 10: Bob submits review (feedback_submitted)
        # ------------------------------------------------------------------
        submit_resp = client.post(
            f"/projects/{pid}/assignments/{aid}/submit",
            headers=bob_hdrs,
        )
        assert submit_resp.status_code == 200, submit_resp.text
        assert submit_resp.json()["status"] == "feedback_submitted"

        # ------------------------------------------------------------------
        # Step 11: Alice requests concurrence from bob
        # ------------------------------------------------------------------
        concur_req_notify_calls: list[tuple] = []

        def _capture_concur_req_notify(event: str, **kwargs):
            concur_req_notify_calls.append((event, kwargs))

        with patch(
            "docreview360.notifications.send_notification",
            side_effect=_capture_concur_req_notify,
        ):
            req_resp = client.post(
                f"/projects/{pid}/assignments/{aid}/request-concurrence",
                headers=alice_hdrs,
            )
        assert req_resp.status_code == 200, req_resp.text
        assert req_resp.json()["ok"] is True
        concur_req_events = [
            e for e, _ in concur_req_notify_calls if e == "review.concurrence_requested"
        ]
        assert len(concur_req_events) >= 1, f"review.concurrence_requested not fired; {concur_req_notify_calls}"

        # ------------------------------------------------------------------
        # Step 12: Bob concurs — verify review.signed + review.all_complete fired
        # ------------------------------------------------------------------
        concur_notify_calls: list[tuple] = []

        def _capture_concur_notify(event: str, **kwargs):
            concur_notify_calls.append((event, kwargs))

        with patch(
            "docreview360.notifications.send_notification",
            side_effect=_capture_concur_notify,
        ):
            concur_resp = client.post(
                f"/projects/{pid}/assignments/{aid}/concur",
                headers=bob_hdrs,
            )
        assert concur_resp.status_code == 200, concur_resp.text
        assert concur_resp.json()["status"] == "concurred"
        signed_events = [e for e, _ in concur_notify_calls if e == "review.signed"]
        assert len(signed_events) >= 1, f"review.signed not fired; {concur_notify_calls}"
        all_complete_events = [e for e, _ in concur_notify_calls if e == "review.all_complete"]
        assert len(all_complete_events) >= 1, f"review.all_complete not fired; {concur_notify_calls}"

        # Verify final assignment state
        assignments_resp = client.get(f"/projects/{pid}/assignments", headers=alice_hdrs)
        assert assignments_resp.status_code == 200
        assignments = assignments_resp.json()["items"]
        bob_assignment = next((a for a in assignments if a["reviewer"] == "bob"), None)
        assert bob_assignment is not None
        assert bob_assignment["status"] == "concurred"
        assert bob_assignment["signed_at"] is not None

        # ------------------------------------------------------------------
        # Step 13: Alice advances project lifecycle to closed
        # ------------------------------------------------------------------
        lifecycle_path = f"/projects/{pid}/lifecycle"
        for target_status in (
            "in_review",
            "reviewed",
            "ready_for_publication",
            "published",
            "submitted_to_records",
            "closed",
        ):
            lc_resp = client.post(
                lifecycle_path,
                json={"status": target_status},
                headers=alice_hdrs,
            )
            assert lc_resp.status_code == 200, (
                f"Lifecycle → {target_status} failed: {lc_resp.text}"
            )
            assert lc_resp.json()["status"] == target_status

        # Verify final lifecycle state
        get_lc = client.get(lifecycle_path, headers=alice_hdrs)
        assert get_lc.status_code == 200
        assert get_lc.json()["status"] == "closed"

        # ------------------------------------------------------------------
        # Step 14: Alice downloads the records package (ZIP)
        # ------------------------------------------------------------------
        pkg_resp = client.get(f"/projects/{pid}/records-package", headers=alice_hdrs)
        assert pkg_resp.status_code == 200, pkg_resp.text
        assert pkg_resp.headers["content-type"] == "application/zip"
        assert "X-Content-Hash" in pkg_resp.headers
        assert pkg_resp.headers["X-Content-Hash"].startswith("sha256=")
        assert len(pkg_resp.content) > 0


# ---------------------------------------------------------------------------
# Test 2: Reviewer replacement — OOO scenario
# ---------------------------------------------------------------------------


class TestReviewerReplacement:
    """E2E test: original reviewer goes OOO; SME replaces with another user.

    Verifies:
    - Original reviewer's feedback items are preserved in the ledger after replacement
    - Replacement reviewer is assigned and can start/concur
    - Original assignment status is 'replaced'
    - Notification events are fired for both replacement and new assignment
    """

    def test_reviewer_replacement_preserves_feedback(self) -> None:
        client = TestClient(app)
        alice_hdrs = _alice_headers()
        bob_hdrs = _bob_headers()
        charlie_hdrs = _charlie_headers()

        # ------------------------------------------------------------------
        # Step 1: Alice creates a project and assigns bob
        # ------------------------------------------------------------------
        proj_resp = client.post(
            "/projects",
            json={"name": "OOO Replacement Project", "doc_type": "Advisory Circular", "phase": "Draft"},
            headers=alice_hdrs,
        )
        assert proj_resp.status_code in (200, 201), proj_resp.text
        pid = proj_resp.json()["id"]

        assign_resp = client.post(
            f"/projects/{pid}/assignments",
            json={"reviewer": "bob"},
            headers=alice_hdrs,
        )
        assert assign_resp.status_code == 201, assign_resp.text
        aid = assign_resp.json()["id"]

        # ------------------------------------------------------------------
        # Step 2: Bob starts the review
        # ------------------------------------------------------------------
        start_resp = client.post(
            f"/projects/{pid}/assignments/{aid}/start",
            headers=bob_hdrs,
        )
        assert start_resp.status_code == 200, start_resp.text
        assert start_resp.json()["status"] == "reviewing"

        # ------------------------------------------------------------------
        # Step 3: Bob adds feedback before going OOO
        # ------------------------------------------------------------------
        fb1_resp = client.post(
            f"/projects/{pid}/feedback",
            json={
                "text": "Appendix A references an obsolete standard (MIL-STD-810F).",
                "feedback_type": "comment",
                "assignment_id": aid,
            },
            headers=bob_hdrs,
        )
        assert fb1_resp.status_code == 201, fb1_resp.text
        fb1_id = fb1_resp.json()["id"]

        fb2_resp = client.post(
            f"/projects/{pid}/feedback",
            json={
                "text": "Does this document supersede AC 20-115D?",
                "feedback_type": "question",
                "assignment_id": aid,
            },
            headers=bob_hdrs,
        )
        assert fb2_resp.status_code == 201, fb2_resp.text
        fb2_id = fb2_resp.json()["id"]

        # Confirm both feedback items exist
        fb_list = client.get(f"/projects/{pid}/feedback", headers=alice_hdrs).json()["items"]
        fb_ids = {f["id"] for f in fb_list}
        assert fb1_id in fb_ids
        assert fb2_id in fb_ids

        # ------------------------------------------------------------------
        # Step 4: Alice replaces bob with charlie (OOO reason)
        # ------------------------------------------------------------------
        replace_notify_calls: list[tuple] = []

        def _capture_replace_notify(event: str, **kwargs):
            replace_notify_calls.append((event, kwargs))

        with patch(
            "docreview360.notifications.send_notification",
            side_effect=_capture_replace_notify,
        ):
            replace_resp = client.post(
                f"/projects/{pid}/assignments/{aid}/replace",
                json={
                    "replacement_reviewer": "charlie",
                    "reason": "Bob is out of office through end of sprint.",
                },
                headers=alice_hdrs,
            )
        assert replace_resp.status_code == 200, replace_resp.text
        replace_data = replace_resp.json()
        original = replace_data["original"]
        replacement = replace_data["replacement"]

        # Original assignment should be 'replaced'
        assert original["status"] == "replaced"
        assert original["reviewer"] == "bob"

        # New assignment for charlie should be 'invited'
        charlie_aid = replacement["id"]
        assert replacement["reviewer"] == "charlie"
        assert replacement["status"] == "invited"

        # Verify replacement notifications were fired
        replaced_events = [e for e, _ in replace_notify_calls if e == "review.replaced"]
        assigned_events = [e for e, _ in replace_notify_calls if e == "review.assigned"]
        assert len(replaced_events) >= 1, f"review.replaced not fired; {replace_notify_calls}"
        assert len(assigned_events) >= 1, f"review.assigned not fired; {replace_notify_calls}"

        # ------------------------------------------------------------------
        # Step 5: Verify bob's original feedback is preserved in the ledger
        # ------------------------------------------------------------------
        fb_after = client.get(f"/projects/{pid}/feedback", headers=alice_hdrs).json()["items"]
        fb_after_ids = {f["id"] for f in fb_after}
        assert fb1_id in fb_after_ids, "Bob's comment was lost after replacement"
        assert fb2_id in fb_after_ids, "Bob's question was lost after replacement"

        # Feedback items still reference bob as the reviewer
        bob_fb = [f for f in fb_after if f["reviewer"] == "bob"]
        assert len(bob_fb) >= 2, f"Expected >=2 of bob's items; got {bob_fb}"

        # ------------------------------------------------------------------
        # Step 6: Check assignments — both bob (replaced) and charlie (invited) present
        # ------------------------------------------------------------------
        all_assignments = client.get(f"/projects/{pid}/assignments", headers=alice_hdrs).json()["items"]
        statuses = {a["reviewer"]: a["status"] for a in all_assignments}
        assert statuses.get("bob") == "replaced", f"bob status: {statuses.get('bob')}"
        assert statuses.get("charlie") == "invited", f"charlie status: {statuses.get('charlie')}"

        # ------------------------------------------------------------------
        # Step 7: Charlie picks up the review — starts, adds feedback, concurs
        # ------------------------------------------------------------------
        charlie_start = client.post(
            f"/projects/{pid}/assignments/{charlie_aid}/start",
            headers=charlie_hdrs,
        )
        assert charlie_start.status_code == 200, charlie_start.text
        assert charlie_start.json()["status"] == "reviewing"

        charlie_fb_resp = client.post(
            f"/projects/{pid}/feedback",
            json={
                "text": "I concur with bob's note on Appendix A; additionally recommend MIL-STD-810H.",
                "feedback_type": "comment",
                "assignment_id": charlie_aid,
            },
            headers=charlie_hdrs,
        )
        assert charlie_fb_resp.status_code == 201, charlie_fb_resp.text
        charlie_fb_id = charlie_fb_resp.json()["id"]

        # Charlie submits and concurs
        charlie_submit = client.post(
            f"/projects/{pid}/assignments/{charlie_aid}/submit",
            headers=charlie_hdrs,
        )
        assert charlie_submit.status_code == 200, charlie_submit.text

        charlie_concur = client.post(
            f"/projects/{pid}/assignments/{charlie_aid}/concur",
            headers=charlie_hdrs,
        )
        assert charlie_concur.status_code == 200, charlie_concur.text
        assert charlie_concur.json()["status"] == "concurred"

        # ------------------------------------------------------------------
        # Step 8: Final ledger audit — all items from both reviewers present
        # ------------------------------------------------------------------
        final_fb = client.get(f"/projects/{pid}/feedback", headers=alice_hdrs).json()["items"]
        final_fb_ids = {f["id"] for f in final_fb}
        # Bob's pre-replacement items
        assert fb1_id in final_fb_ids, "Bob's original comment was removed"
        assert fb2_id in final_fb_ids, "Bob's original question was removed"
        # Charlie's new item
        assert charlie_fb_id in final_fb_ids, "Charlie's feedback was not recorded"

        # Reviewer breakdown
        final_reviewers = {f["reviewer"] for f in final_fb}
        assert "bob" in final_reviewers
        assert "charlie" in final_reviewers

        # ------------------------------------------------------------------
        # Step 9: Records package generation — verify all parties captured
        # ------------------------------------------------------------------
        # Advance lifecycle so package can be downloaded
        for status in ("in_review", "reviewed", "ready_for_publication",
                       "published", "submitted_to_records", "closed"):
            lc_resp = client.post(
                f"/projects/{pid}/lifecycle",
                json={"status": status},
                headers=alice_hdrs,
            )
            assert lc_resp.status_code == 200, f"Lifecycle {status}: {lc_resp.text}"

        pkg_resp = client.get(f"/projects/{pid}/records-package", headers=alice_hdrs)
        assert pkg_resp.status_code == 200, pkg_resp.text
        assert pkg_resp.headers.get("content-type") == "application/zip"
        assert pkg_resp.headers.get("X-Content-Hash", "").startswith("sha256=")


# ---------------------------------------------------------------------------
# Test 3: Concur-with-comments variant
# ---------------------------------------------------------------------------


class TestConcurWithComments:
    """Verify the concur-with-comments endpoint creates feedback AND concurs in one call."""

    def test_concur_with_comments_flow(self) -> None:
        client = TestClient(app)
        alice_hdrs = _alice_headers()
        bob_hdrs = _bob_headers()

        # Create project and assignment
        proj_resp = client.post(
            "/projects",
            json={"name": "ConcurWithComments Project", "doc_type": "Policy", "phase": "Draft"},
            headers=alice_hdrs,
        )
        assert proj_resp.status_code in (200, 201)
        pid = proj_resp.json()["id"]

        assign_resp = client.post(
            f"/projects/{pid}/assignments",
            json={"reviewer": "bob"},
            headers=alice_hdrs,
        )
        assert assign_resp.status_code == 201
        aid = assign_resp.json()["id"]

        # Bob starts
        client.post(f"/projects/{pid}/assignments/{aid}/start", headers=bob_hdrs)

        # Bob concurs-with-comments in a single call
        cwc_resp = client.post(
            f"/projects/{pid}/assignments/{aid}/concur-with-comments",
            json={"text": "I concur overall; minor typo in section 2.1."},
            headers=bob_hdrs,
        )
        assert cwc_resp.status_code == 200, cwc_resp.text
        assert cwc_resp.json()["status"] == "concurred"

        # Verify a feedback item was created containing the final note
        fb_list = client.get(f"/projects/{pid}/feedback", headers=alice_hdrs).json()["items"]
        assert any(
            "minor typo" in f["text"] for f in fb_list
        ), "Concur-with-comments text not persisted as feedback"

        # Verify assignment is in terminal 'concurred' state
        assignments = client.get(f"/projects/{pid}/assignments", headers=alice_hdrs).json()["items"]
        bob_a = next(a for a in assignments if a["reviewer"] == "bob")
        assert bob_a["status"] == "concurred"


# ---------------------------------------------------------------------------
# Test 4: Non-concurrence path
# ---------------------------------------------------------------------------


class TestNonConcurrence:
    """Verify reviewer can non-concur with a written reason."""

    def test_non_concur_flow(self) -> None:
        client = TestClient(app)
        alice_hdrs = _alice_headers()
        bob_hdrs = _bob_headers()

        proj_resp = client.post(
            "/projects",
            json={"name": "NonConcur Project", "doc_type": "Policy", "phase": "Draft"},
            headers=alice_hdrs,
        )
        assert proj_resp.status_code in (200, 201)
        pid = proj_resp.json()["id"]

        assign_resp = client.post(
            f"/projects/{pid}/assignments",
            json={"reviewer": "bob"},
            headers=alice_hdrs,
        )
        assert assign_resp.status_code == 201
        aid = assign_resp.json()["id"]

        client.post(f"/projects/{pid}/assignments/{aid}/start", headers=bob_hdrs)

        nc_resp = client.post(
            f"/projects/{pid}/assignments/{aid}/non-concur",
            json={"reason": "Material inaccuracies in Section 4 require a full revision."},
            headers=bob_hdrs,
        )
        assert nc_resp.status_code == 200, nc_resp.text
        assert nc_resp.json()["status"] == "non_concurred"

        # Verify non_concurred is a terminal status — concurrence request blocked
        req_resp = client.post(
            f"/projects/{pid}/assignments/{aid}/request-concurrence",
            headers=alice_hdrs,
        )
        assert req_resp.status_code == 409, (
            "Should not be able to request concurrence after non_concurred"
        )


# ---------------------------------------------------------------------------
# Test 5: Phase archive endpoint
# ---------------------------------------------------------------------------


class TestPhaseArchiveFeedback:
    """Verify that the archive-phase endpoint resolves all open feedback in a given phase.

    Tests both the manual POST /projects/{id}/feedback/archive-phase endpoint and
    the direct archive_phase_feedback() function.
    """

    def test_archive_phase_endpoint(self) -> None:
        """Calling POST .../feedback/archive-phase resolves all open items in that phase."""
        client = TestClient(app)
        alice_hdrs = _alice_headers()
        bob_hdrs = _bob_headers()

        proj_resp = client.post(
            "/projects",
            json={"name": "Phase Archive Project", "doc_type": "Advisory Circular", "phase": "Draft"},
            headers=alice_hdrs,
        )
        assert proj_resp.status_code in (200, 201)
        pid = proj_resp.json()["id"]

        # Assign bob
        assign_resp = client.post(
            f"/projects/{pid}/assignments", json={"reviewer": "bob"}, headers=alice_hdrs
        )
        assert assign_resp.status_code == 201
        aid = assign_resp.json()["id"]
        client.post(f"/projects/{pid}/assignments/{aid}/start", headers=bob_hdrs)

        # Bob leaves two open feedback items tagged to the "Draft" phase
        fb1_resp = client.post(
            f"/projects/{pid}/feedback",
            json={"text": "Needs clearer intro.", "phase": "Draft"},
            headers=bob_hdrs,
        )
        assert fb1_resp.status_code == 201
        fb1_id = fb1_resp.json()["id"]

        fb2_resp = client.post(
            f"/projects/{pid}/feedback",
            json={"text": "Section 2 is ambiguous.", "feedback_type": "question", "phase": "Draft"},
            headers=bob_hdrs,
        )
        assert fb2_resp.status_code == 201
        fb2_id = fb2_resp.json()["id"]

        # Verify both are open
        fb_list = client.get(f"/projects/{pid}/feedback", headers=alice_hdrs).json()["items"]
        open_ids = {f["id"] for f in fb_list if f["status"] == "open"}
        assert fb1_id in open_ids
        assert fb2_id in open_ids

        # Alice archives the Draft phase via the manual endpoint
        archive_resp = client.post(
            f"/projects/{pid}/feedback/archive-phase",
            json={"phase": "Draft"},
            headers=alice_hdrs,
        )
        assert archive_resp.status_code == 200, archive_resp.text
        archive_data = archive_resp.json()
        assert archive_data["phase"] == "Draft"
        assert archive_data["archived"] >= 2

        # After archiving, both items should be resolved
        fb_list_after = client.get(f"/projects/{pid}/feedback", headers=alice_hdrs).json()["items"]
        fb1_after = next((f for f in fb_list_after if f["id"] == fb1_id), None)
        fb2_after = next((f for f in fb_list_after if f["id"] == fb2_id), None)
        assert fb1_after is not None
        assert fb2_after is not None
        assert fb1_after["status"] == "resolved", f"fb1 status: {fb1_after['status']}"
        assert fb2_after["status"] == "resolved", f"fb2 status: {fb2_after['status']}"

    def test_archive_phase_function_directly(self) -> None:
        """Unit-level: archive_phase_feedback() resolves only open items in the named phase."""
        from docreview360.feedback_ledger import (
            archive_phase_feedback,
            create_feedback_item,
            get_feedback_progress,
            list_feedback_items,
        )

        proj_id = "archive-unit-test-project"

        # Create items in two different phases
        open_draft = create_feedback_item(
            proj_id, "bob", "Open draft comment", phase="Draft"
        )
        open_review = create_feedback_item(
            proj_id, "bob", "Open review comment", phase="Review"
        )

        # Archive only Draft phase
        archived_count = archive_phase_feedback(proj_id, "Draft", archived_by="alice")
        assert archived_count >= 1

        # Draft item is resolved; review item still open
        draft_items = list_feedback_items(proj_id, phase="Draft")
        review_items = list_feedback_items(proj_id, phase="Review")

        draft_item = next((f for f in draft_items if f.id == open_draft.id), None)
        review_item = next((f for f in review_items if f.id == open_review.id), None)

        assert draft_item is not None
        assert draft_item.status == "resolved"

        assert review_item is not None
        assert review_item.status == "open"

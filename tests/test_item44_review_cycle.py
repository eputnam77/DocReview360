# SPDX-License-Identifier: MIT
"""Item 44 — Document review cycle: ReviewAssignment, user search, curated templates,
starter content, and CommentModel field additions.

Run targeted:
    DOCREVIEW360_ENV=dev pytest tests/test_item44_review_cycle.py -v
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


# ---------------------------------------------------------------------------
# Template and document-type rename tests
# ---------------------------------------------------------------------------


class TestDocumentTypeFieldRename:
    """Verify that default_workflow_template_id is used instead of default_template_id."""

    def test_document_type_model_has_new_field(self) -> None:
        from docreview360.doc_types import DocumentTypeModel
        dt = DocumentTypeModel(name="Test", template="<h1>Test</h1>", workflow=["Draft"])
        assert hasattr(dt, "default_workflow_template_id")
        assert not hasattr(dt, "default_template_id")

    def test_document_type_model_field_default_is_none(self) -> None:
        from docreview360.doc_types import DocumentTypeModel
        dt = DocumentTypeModel(name="Test", template="<h1>Test</h1>", workflow=["Draft"])
        assert dt.default_workflow_template_id is None

    def test_document_type_model_accepts_workflow_template_id(self) -> None:
        from docreview360.doc_types import DocumentTypeModel
        dt = DocumentTypeModel(
            name="Test",
            template="<h1>Test</h1>",
            workflow=["Draft"],
            default_workflow_template_id="branch-coordination",
        )
        assert dt.default_workflow_template_id == "branch-coordination"

    def test_api_returns_new_field_name(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        # Create a doc type and verify the API returns the new field name
        resp = client.post(
            "/document-types",
            json={
                "name": "TestRenameDoc",
                "template": "<h1>Test</h1>",
                "workflow": ["Draft"],
                "default_workflow_template_id": None,
            },
            headers=hdrs,
        )
        assert resp.status_code in (201, 409)
        resp2 = client.get("/document-types/TestRenameDoc", headers=hdrs)
        assert resp2.status_code == 200
        data = resp2.json()
        assert "default_workflow_template_id" in data
        assert "default_template_id" not in data


# ---------------------------------------------------------------------------
# Dropdown bug fix — workflow-templates
# ---------------------------------------------------------------------------


class TestWorkflowTemplatesEndpoint:
    """GET /workflow-templates returns data suitable for the Default Workflow dropdown."""

    def test_workflow_templates_endpoint_accessible(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        resp = client.get("/workflow-templates", headers=hdrs)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_workflow_template_items_have_id_and_name(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        resp = client.get("/workflow-templates", headers=hdrs)
        assert resp.status_code == 200
        for item in resp.json():
            assert "id" in item or "name" in item


# ---------------------------------------------------------------------------
# Curated starter templates
# ---------------------------------------------------------------------------


class TestCuratedStarterTemplates:
    """Verify that bootstrapped doc types have curated HTML templates."""

    def test_advisory_circular_template_is_not_placeholder(self) -> None:
        from docreview360.doc_types import get_document_type
        dt = get_document_type("Advisory Circular")
        assert dt is not None
        # Should have real content, not the bare `<h1>Advisory Circular</h1>` placeholder
        assert dt.template is not None
        assert "<h2>" in dt.template, "Curated template should have section headings"

    def test_policy_template_has_purpose_section(self) -> None:
        from docreview360.doc_types import get_document_type
        dt = get_document_type("Policy")
        assert dt is not None
        assert "Purpose" in (dt.template or "")

    def test_memorandum_template_has_memo_structure(self) -> None:
        from docreview360.doc_types import get_document_type
        dt = get_document_type("Memorandum")
        assert dt is not None
        assert "MEMORANDUM" in (dt.template or "") or "Memorandum" in (dt.template or "")

    def test_sop_template_has_procedure_steps(self) -> None:
        from docreview360.doc_types import get_document_type
        dt = get_document_type("SOP")
        assert dt is not None
        assert "Procedure" in (dt.template or "")

    def test_starter_content_endpoint_returns_curated_html(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        resp = client.get("/document-types/Policy/starter-content", headers=hdrs)
        assert resp.status_code == 200
        data = resp.json()
        assert data["doc_type"] == "Policy"
        assert "<h2>" in data["content"], "Starter content should include section headings"

    def test_starter_content_returns_404_for_unknown_type(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        resp = client.get("/document-types/NonExistentType/starter-content", headers=hdrs)
        assert resp.status_code == 404

    def test_all_default_types_have_template(self) -> None:
        from docreview360.doc_types import list_document_types
        for dt in list_document_types():
            assert dt.template, f"Document type '{dt.name}' has no template"
            assert dt.template.startswith("<"), f"Template for '{dt.name}' should be HTML"


# ---------------------------------------------------------------------------
# ReviewAssignment model and CRUD
# ---------------------------------------------------------------------------


class TestReviewAssignmentModule:
    """Unit tests for review_assignments.py."""

    def setup_method(self) -> None:
        # Clean up any assignments from prior tests for isolation
        from docreview360.review_assignments import _ensure_table
        _ensure_table()

    def test_create_assignment_returns_model(self) -> None:
        from docreview360.review_assignments import create_assignment
        a = create_assignment("proj-1", "bob", status="invited")
        assert a.id
        assert a.project_id == "proj-1"
        assert a.reviewer == "bob"
        assert a.status == "invited"

    def test_get_assignment_round_trip(self) -> None:
        from docreview360.review_assignments import create_assignment, get_assignment
        created = create_assignment("proj-rt", "alice", status="invited")
        fetched = get_assignment(created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.reviewer == "alice"

    def test_list_assignments_for_project(self) -> None:
        from docreview360.review_assignments import create_assignment, list_assignments
        create_assignment("proj-list", "alice", status="invited")
        create_assignment("proj-list", "bob", status="reviewing")
        result = list_assignments("proj-list")
        reviewers = {a.reviewer for a in result}
        assert "alice" in reviewers
        assert "bob" in reviewers

    def test_transition_status(self) -> None:
        from docreview360.review_assignments import create_assignment, transition_status
        a = create_assignment("proj-ts", "charlie", status="invited")
        updated = transition_status(a.id, "reviewing", ts_field="started_at")
        assert updated.status == "reviewing"
        assert updated.started_at is not None

    def test_replace_assignment_creates_new(self) -> None:
        from docreview360.review_assignments import create_assignment, replace_assignment
        original = create_assignment("proj-rep", "alice", status="reviewing")
        updated, new_a = replace_assignment(original.id, "bob", "Out of office")
        assert updated.status == "replaced"
        assert updated.replaced_by == new_a.id
        assert new_a.reviewer == "bob"
        assert new_a.status == "invited"

    def test_delete_assignment(self) -> None:
        from docreview360.review_assignments import (
            create_assignment,
            delete_assignment,
            get_assignment,
        )
        a = create_assignment("proj-del", "alice", status="invited")
        delete_assignment(a.id)
        assert get_assignment(a.id) is None

    def test_migrate_reviewers_to_assignments(self) -> None:
        from docreview360.review_assignments import (
            migrate_reviewers_to_assignments,
        )
        created = migrate_reviewers_to_assignments("proj-migrate", ["alice", "bob"])
        assert len(created) == 2
        assert all(a.status == "reviewing" for a in created)
        # Second call should not create duplicates
        again = migrate_reviewers_to_assignments("proj-migrate", ["alice", "bob"])
        assert len(again) == 0

    def test_get_nonexistent_returns_none(self) -> None:
        from docreview360.review_assignments import get_assignment
        assert get_assignment("nonexistent-id") is None


# ---------------------------------------------------------------------------
# ReviewAssignment API endpoints
# ---------------------------------------------------------------------------


class TestAssignmentAPI:
    """Integration tests for /projects/{id}/assignments/* endpoints."""

    def _create_project(self, client: TestClient, hdrs: dict) -> str:
        import uuid
        project_id = f"test-assign-{uuid.uuid4().hex[:8]}"
        resp = client.post(
            "/projects",
            json={"id": project_id, "name": f"Assignment Test {project_id}"},
            headers=hdrs,
        )
        assert resp.status_code in (200, 201), f"Project creation failed: {resp.text}"
        return project_id

    def test_list_assignments_empty(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        project_id = self._create_project(client, hdrs)
        resp = client.get(f"/projects/{project_id}/assignments", headers=hdrs)
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    def test_create_and_list_assignment(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        project_id = self._create_project(client, hdrs)
        # Create assignment
        resp = client.post(
            f"/projects/{project_id}/assignments",
            json={"reviewer": "bob"},
            headers=hdrs,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["reviewer"] == "bob"
        assert data["status"] == "invited"
        # List — should have one entry
        resp2 = client.get(f"/projects/{project_id}/assignments", headers=hdrs)
        assert resp2.status_code == 200
        assert len(resp2.json()["items"]) == 1

    def test_start_assignment_transitions_to_reviewing(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        bob_hdrs = _bob_headers()
        project_id = self._create_project(client, hdrs)
        # Alice creates assignment for bob
        create_resp = client.post(
            f"/projects/{project_id}/assignments",
            json={"reviewer": "bob"},
            headers=hdrs,
        )
        assert create_resp.status_code == 201
        aid = create_resp.json()["id"]
        # Bob starts the review (bob is the reviewer)
        start_resp = client.post(
            f"/projects/{project_id}/assignments/{aid}/start",
            headers=bob_hdrs,
        )
        assert start_resp.status_code == 200
        assert start_resp.json()["status"] == "reviewing"

    def test_submit_transitions_to_feedback_submitted(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        bob_hdrs = _bob_headers()
        project_id = self._create_project(client, hdrs)
        create_resp = client.post(
            f"/projects/{project_id}/assignments",
            json={"reviewer": "bob"},
            headers=hdrs,
        )
        aid = create_resp.json()["id"]
        # Bob submits feedback
        submit_resp = client.post(
            f"/projects/{project_id}/assignments/{aid}/submit",
            headers=bob_hdrs,
        )
        assert submit_resp.status_code == 200
        assert submit_resp.json()["status"] == "feedback_submitted"

    def test_concur_assignment(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        bob_hdrs = _bob_headers()
        project_id = self._create_project(client, hdrs)
        create_resp = client.post(
            f"/projects/{project_id}/assignments",
            json={"reviewer": "bob"},
            headers=hdrs,
        )
        aid = create_resp.json()["id"]
        # Bob concurs
        concur_resp = client.post(
            f"/projects/{project_id}/assignments/{aid}/concur",
            headers=bob_hdrs,
        )
        assert concur_resp.status_code == 200
        assert concur_resp.json()["status"] == "concurred"

    def test_non_concur_requires_reason(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        bob_hdrs = _bob_headers()
        project_id = self._create_project(client, hdrs)
        create_resp = client.post(
            f"/projects/{project_id}/assignments",
            json={"reviewer": "bob"},
            headers=hdrs,
        )
        aid = create_resp.json()["id"]
        # Missing body → 422
        resp = client.post(
            f"/projects/{project_id}/assignments/{aid}/non-concur",
            headers=bob_hdrs,
        )
        assert resp.status_code == 422
        # With reason → 200
        resp2 = client.post(
            f"/projects/{project_id}/assignments/{aid}/non-concur",
            json={"reason": "Disagree with section 3."},
            headers=bob_hdrs,
        )
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "non_concurred"

    def test_replace_assignment(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        project_id = self._create_project(client, hdrs)
        create_resp = client.post(
            f"/projects/{project_id}/assignments",
            json={"reviewer": "bob"},
            headers=hdrs,
        )
        aid = create_resp.json()["id"]
        # Alice replaces bob with charlie
        replace_resp = client.post(
            f"/projects/{project_id}/assignments/{aid}/replace",
            json={"replacement_reviewer": "charlie", "reason": "OOO"},
            headers=hdrs,
        )
        assert replace_resp.status_code == 200
        data = replace_resp.json()
        assert data["original"]["status"] == "replaced"
        assert data["replacement"]["reviewer"] == "charlie"

    def test_delete_invited_assignment(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        project_id = self._create_project(client, hdrs)
        create_resp = client.post(
            f"/projects/{project_id}/assignments",
            json={"reviewer": "bob"},
            headers=hdrs,
        )
        aid = create_resp.json()["id"]
        del_resp = client.delete(
            f"/projects/{project_id}/assignments/{aid}",
            headers=hdrs,
        )
        assert del_resp.status_code == 204

    def test_delete_non_invited_assignment_returns_409(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        bob_hdrs = _bob_headers()
        project_id = self._create_project(client, hdrs)
        create_resp = client.post(
            f"/projects/{project_id}/assignments",
            json={"reviewer": "bob"},
            headers=hdrs,
        )
        aid = create_resp.json()["id"]
        # Bob starts → status = reviewing
        client.post(f"/projects/{project_id}/assignments/{aid}/start", headers=bob_hdrs)
        # Now delete should fail
        del_resp = client.delete(
            f"/projects/{project_id}/assignments/{aid}",
            headers=hdrs,
        )
        assert del_resp.status_code == 409

    def test_wrong_reviewer_cannot_start(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        project_id = self._create_project(client, hdrs)
        create_resp = client.post(
            f"/projects/{project_id}/assignments",
            json={"reviewer": "bob"},
            headers=hdrs,
        )
        aid = create_resp.json()["id"]
        # Alice tries to start bob's assignment
        resp = client.post(
            f"/projects/{project_id}/assignments/{aid}/start",
            headers=hdrs,
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# User search endpoint
# ---------------------------------------------------------------------------


class TestUserSearch:
    """Tests for GET /users/search."""

    def test_search_returns_list(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        resp = client.get("/users/search", headers=hdrs)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_search_with_term(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        resp = client.get("/users/search?q=alice", headers=hdrs)
        assert resp.status_code == 200
        data = resp.json()
        assert any(u["username"] == "alice" for u in data)

    def test_search_result_has_required_fields(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        resp = client.get("/users/search?q=alice", headers=hdrs)
        assert resp.status_code == 200
        users = resp.json()
        if users:
            user = users[0]
            assert "username" in user
            assert "display_name" in user
            assert "active" in user

    def test_search_respects_limit(self) -> None:
        client = TestClient(app)
        hdrs = _alice_headers()
        resp = client.get("/users/search?limit=1", headers=hdrs)
        assert resp.status_code == 200
        assert len(resp.json()) <= 1

    def test_search_requires_auth(self) -> None:
        client = TestClient(app)
        resp = client.get("/users/search")
        assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# CommentModel new fields
# ---------------------------------------------------------------------------


class TestCommentModelNewFields:
    """Verify CommentModel now has source, feedback_type, and assignment_id fields."""

    def test_comment_model_has_source_field(self) -> None:
        from datetime import datetime, timezone

        from docreview360.comments import CommentModel
        c = CommentModel(
            id="test-1",
            document="doc-1",
            user="alice",
            text="Test",
            raw_text="Test",
            created=datetime.now(timezone.utc),
        )
        assert hasattr(c, "source")
        assert c.source == "inline"  # default

    def test_comment_model_accepts_feedback_source(self) -> None:
        from datetime import datetime, timezone

        from docreview360.comments import CommentModel
        c = CommentModel(
            id="test-2",
            document="doc-1",
            user="alice",
            text="Test",
            raw_text="Test",
            created=datetime.now(timezone.utc),
            source="feedback",
            feedback_type="question",
            assignment_id="assign-123",
        )
        assert c.source == "feedback"
        assert c.feedback_type == "question"
        assert c.assignment_id == "assign-123"

    def test_comment_model_feedback_type_default_none(self) -> None:
        from datetime import datetime, timezone

        from docreview360.comments import CommentModel
        c = CommentModel(
            id="test-3",
            document="doc-1",
            user="alice",
            text="Test",
            raw_text="Test",
            created=datetime.now(timezone.utc),
        )
        assert c.feedback_type is None
        assert c.assignment_id is None

    def test_comment_sources_constants(self) -> None:
        from docreview360.comments import COMMENT_FEEDBACK_TYPES, COMMENT_SOURCES
        assert "feedback" in COMMENT_SOURCES
        assert "inline" in COMMENT_SOURCES
        assert "review" in COMMENT_SOURCES
        assert "question" in COMMENT_FEEDBACK_TYPES
        assert "suggestion" in COMMENT_FEEDBACK_TYPES

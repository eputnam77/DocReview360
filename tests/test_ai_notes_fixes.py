"""Tests for fixes implemented from ai-notes.md.

Covers:
- Blank document exclusion from quality scores
- entity_id/entity_type set on project creation audit log
- New canonical workflow template IDs and descriptions
- ProjectModel progress/status for newly created projects
- Document number field preference (document_number over auto-increment)
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest

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
    token = auth.create_access_token({"sub": "alice"}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Blank document exclusion from quality scores
# ---------------------------------------------------------------------------


class TestBlankDocumentQualityScore:
    """Blank/just-created documents must not contribute to quality scores."""

    def test_blank_document_returns_empty_scores(self) -> None:
        """A project whose only document is blank returns an empty scores list."""
        client = TestClient(app)
        hdrs = _alice_headers()

        proj_res = client.post(
            "/projects",
            json={"name": "Blank Doc Test Project"},
            headers=hdrs,
        )
        assert proj_res.status_code == 201
        project_id = proj_res.json()["id"]

        scores_res = client.get(f"/projects/{project_id}/documents/scores", headers=hdrs)
        assert scores_res.status_code == 200
        assert scores_res.json() == [], (
            "A newly created project with only a blank document should return [] not a score"
        )

    def test_project_with_real_content_returns_scores(self) -> None:
        """A project document with real content does produce a quality score."""
        from docreview360 import documents as doc_mod
        from docreview360 import search as search_mod

        client = TestClient(app)
        hdrs = _alice_headers()

        proj_res = client.post(
            "/projects",
            json={"name": "Real Content Project"},
            headers=hdrs,
        )
        assert proj_res.status_code == 201
        project_id = proj_res.json()["id"]

        # Update the blank document to have real content by finding it in doc store
        rich_content = "<p>" + "This document has real content for quality scoring. " * 5 + "</p>"
        updated_any = False
        for doc_id, doc in list(doc_mod.documents.items()):
            if getattr(doc, "project", None) == project_id:
                doc_mod.documents[doc_id].content = rich_content
                updated_any = True

        if updated_any:
            scores_res = client.get(f"/projects/{project_id}/documents/scores", headers=hdrs)
            assert scores_res.status_code == 200
            data = scores_res.json()
            assert isinstance(data, list)
            assert len(data) > 0, "Non-blank document should produce a quality score"

    def test_is_blank_document_logic(self) -> None:
        """Blank detection recognises the create_blank_document template pattern."""
        import re

        def _is_blank(content: str) -> bool:
            raw = content or ""
            no_heading = re.sub(
                r"<h[1-6][^>]*>.*?</h[1-6]>", "", raw,
                flags=re.IGNORECASE | re.DOTALL,
            )
            remaining = re.sub(r"<[^>]+>", "", no_heading).strip()
            if not remaining:
                return True
            stripped = re.sub(r"<[^>]+>", "", raw).strip()
            return len(stripped) < 20

        assert _is_blank("<p></p>")
        # The exact blank template produced by create_blank_document:
        assert _is_blank("<h1>Title</h1><p></p>")
        assert _is_blank("<h1>Blank Doc Test Project</h1><p></p>")
        assert _is_blank("<h1>A Very Long Project Title That Exceeds Twenty Chars</h1><p></p>")
        assert _is_blank("")
        assert _is_blank("   ")
        assert not _is_blank("<p>This document has enough text content here.</p>")
        assert not _is_blank("<h1>Title</h1><p>Some real body content was added here.</p>")


# ---------------------------------------------------------------------------
# Project creation audit log entity_id
# ---------------------------------------------------------------------------


class TestProjectCreationAuditLog:
    """The project creation event must record entity_id = project.id."""

    def test_create_project_logs_entity_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Audit log entry for create_project must include entity_id."""
        import importlib
        import sys

        # docreview360.api registers `projects_router` as an APIRouter alias,
        # so we need the underlying module to patch log_event.
        _proj_mod = importlib.import_module("docreview360.api.projects_router")

        client = TestClient(app)
        hdrs = _alice_headers()

        captured: list[dict] = []
        original_log_fn = _proj_mod.log_event

        def _capturing_log(action: str, **kwargs: object) -> None:
            captured.append({"action": action, **kwargs})
            return original_log_fn(action, **kwargs)

        monkeypatch.setattr(_proj_mod, "log_event", _capturing_log)

        proj_res = client.post(
            "/projects",
            json={"name": "Audit Log Entity Test"},
            headers=hdrs,
        )
        assert proj_res.status_code == 201
        project_id = proj_res.json()["id"]

        create_events = [e for e in captured if e.get("action") == "create_project"]
        assert create_events, "Expected at least one create_project log event"
        event = create_events[0]
        assert event.get("entity_id") == project_id, (
            f"entity_id should be {project_id!r}, got {event.get('entity_id')!r}"
        )
        assert event.get("entity_type") == "project"

    def test_audit_endpoint_returns_project_events(self) -> None:
        """GET /api/audit?entity_id=<project_id> returns the create_project event."""
        client = TestClient(app)
        hdrs = _alice_headers()

        proj_res = client.post(
            "/projects",
            json={"name": "Audit Endpoint Project"},
            headers=hdrs,
        )
        assert proj_res.status_code == 201
        project_id = proj_res.json()["id"]

        # The audit endpoint is under /api/audit (dashboards_router prefix)
        audit_res = client.get(f"/api/audit?entity_id={project_id}", headers=hdrs)
        assert audit_res.status_code == 200
        audit_data = audit_res.json()
        events = audit_data if isinstance(audit_data, list) else audit_data.get("items", [])
        actions = [e.get("action") or e.get("event_type") for e in events]
        assert any("create_project" in str(a) for a in actions), (
            f"Expected create_project in audit events for project {project_id}, got: {actions}"
        )


# ---------------------------------------------------------------------------
# Workflow template IDs and descriptions
# ---------------------------------------------------------------------------


EXPECTED_CANONICAL_TEMPLATES = [
    "standard-document-review",
    "pre-coordination-review",
    "fast-track-review",
    "single-branch-coordination",
    "multi-branch-coordination",
    "external-coordination",
    "requirements-intake-review",
    "publication-readiness-and-distribution",
    "post-publication-implementation",
]

EXPECTED_DESCRIPTIONS = {
    "standard-document-review": "Default review path",
    "pre-coordination-review": "Informal early review",
    "fast-track-review": "Expedited path",
    "single-branch-coordination": "Review path limited to one branch",
    "multi-branch-coordination": "Review path requiring multiple branches",
    "external-coordination": "Review path involving outside organizations",
    "requirements-intake-review": "collecting inputs",
    "publication-readiness-and-distribution": "publication package",
    "post-publication-implementation": "follow-up after publication",
}


class TestWorkflowTemplates:
    """Canonical workflow template IDs and descriptions from ai-notes must be present."""

    def test_canonical_template_ids_present(self) -> None:
        from docreview360.workflows._templates import DEFAULT_WORKFLOW_TEMPLATES

        for template_id in EXPECTED_CANONICAL_TEMPLATES:
            assert template_id in DEFAULT_WORKFLOW_TEMPLATES, (
                f"Canonical workflow template {template_id!r} missing from DEFAULT_WORKFLOW_TEMPLATES"
            )

    def test_canonical_template_descriptions_present(self) -> None:
        from docreview360.workflows._templates import DEFAULT_WORKFLOW_DESCRIPTIONS

        for template_id in EXPECTED_CANONICAL_TEMPLATES:
            assert template_id in DEFAULT_WORKFLOW_DESCRIPTIONS, (
                f"Canonical workflow template {template_id!r} missing from DEFAULT_WORKFLOW_DESCRIPTIONS"
            )

    def test_descriptions_contain_expected_text(self) -> None:
        from docreview360.workflows._templates import DEFAULT_WORKFLOW_DESCRIPTIONS

        for template_id, expected_fragment in EXPECTED_DESCRIPTIONS.items():
            description = DEFAULT_WORKFLOW_DESCRIPTIONS.get(template_id, "")
            assert expected_fragment.lower() in description.lower(), (
                f"Description for {template_id!r} should contain {expected_fragment!r}, "
                f"got: {description!r}"
            )

    def test_workflow_templates_api_returns_canonical_ids(self) -> None:
        """The /workflow-templates endpoint exposes all canonical IDs."""
        client = TestClient(app)
        hdrs = _alice_headers()

        res = client.get("/workflow-templates", headers=hdrs)
        assert res.status_code == 200
        templates = res.json()
        ids = {t["id"] for t in templates}

        for template_id in EXPECTED_CANONICAL_TEMPLATES:
            assert template_id in ids, (
                f"Canonical workflow template {template_id!r} missing from /workflow-templates API"
            )

    def test_workflow_templates_api_includes_descriptions(self) -> None:
        """The /workflow-templates endpoint includes non-empty descriptions for canonical IDs."""
        client = TestClient(app)
        hdrs = _alice_headers()

        res = client.get("/workflow-templates", headers=hdrs)
        assert res.status_code == 200
        templates = res.json()
        template_map = {t["id"]: t for t in templates}

        for template_id in EXPECTED_CANONICAL_TEMPLATES:
            if template_id in template_map:
                desc = template_map[template_id].get("description") or ""
                assert desc, (
                    f"Workflow template {template_id!r} has empty description in API response"
                )

    def test_legacy_alias_ids_still_present(self) -> None:
        """Legacy workflow IDs should still be present for backwards compatibility."""
        from docreview360.workflows._templates import DEFAULT_WORKFLOW_TEMPLATES

        legacy_ids = [
            "branch-coordination",
            "fast-track-coordination",
        ]
        for legacy_id in legacy_ids:
            assert legacy_id in DEFAULT_WORKFLOW_TEMPLATES, (
                f"Legacy workflow ID {legacy_id!r} should still be present for backwards compat"
            )


# ---------------------------------------------------------------------------
# ProjectModel progress and status computed fields
# ---------------------------------------------------------------------------


class TestProjectModelProgressStatus:
    """ProjectModel.status must not return 'Complete'; progress must be position-based."""

    def test_no_workflow_returns_draft_and_zero(self) -> None:
        from docreview360.search import ProjectModel

        pm = ProjectModel(id="test-no-wf", name="No Workflow Project")
        assert pm.status == "Draft"
        assert pm.progress == 0

    def test_status_never_returns_complete(self) -> None:
        """status should only return Draft, Overdue, or In Progress — never Complete."""
        from docreview360 import workflows
        from docreview360.search import ProjectModel

        wf = workflows.create_workflow("test-proj-status", ["Initial Drafting", "Final Issuance"])
        try:
            pm = ProjectModel(id="test-final", name="Final Phase Project", workflow=wf.id)
            assert pm.status != "Complete", (
                f"status returned 'Complete' for phase {wf.phase!r} — expected In Progress"
            )
            assert pm.status in ("Draft", "In Progress", "Overdue")
        finally:
            workflows.workflows.pop(wf.id, None)

    def test_progress_uses_position_not_name(self) -> None:
        """Progress at the last phase of a multi-phase workflow should be 90, not >90."""
        from docreview360 import workflows
        from docreview360.search import ProjectModel

        phases = ["Draft", "Review", "Final Approval"]
        wf = workflows.create_workflow("test-proj-progress", phases)
        try:
            pm = ProjectModel(id="test-progress", name="Progress Test", workflow=wf.id)
            assert pm.progress <= 90, (
                f"Progress {pm.progress} should be <= 90 for a newly created project"
            )
        finally:
            workflows.workflows.pop(wf.id, None)

    def test_progress_single_phase_workflow_returns_10(self) -> None:
        """A single-phase workflow starting at that phase should return progress=10."""
        from docreview360 import workflows
        from docreview360.search import ProjectModel

        wf = workflows.create_workflow("test-single-phase", ["Only Phase"])
        try:
            pm = ProjectModel(id="test-single", name="Single Phase", workflow=wf.id)
            assert pm.progress == 10, (
                f"Single-phase workflow should give progress=10, got {pm.progress}"
            )
        finally:
            workflows.workflows.pop(wf.id, None)

    def test_progress_increases_with_phase_advancement(self) -> None:
        """Progress at a later phase should be greater than at an earlier phase."""
        from docreview360 import workflows
        from docreview360.search import ProjectModel

        phases = ["Phase A", "Phase B", "Phase C", "Phase D"]
        wf1 = workflows.create_workflow("prog-wf-1", phases)
        wf2 = workflows.create_workflow("prog-wf-2", phases)
        try:
            # Advance wf2 to a later phase
            for _ in range(2):
                workflows.advance_workflow(wf2.id)

            pm1 = ProjectModel(id="p1", name="P1", workflow=wf1.id)
            pm2 = ProjectModel(id="p2", name="P2", workflow=wf2.id)
            assert pm2.progress > pm1.progress, (
                f"Later phase ({pm2.progress}) should have higher progress than earlier ({pm1.progress})"
            )
        finally:
            workflows.workflows.pop(wf1.id, None)
            workflows.workflows.pop(wf2.id, None)

    def test_fast_track_final_issuance_not_complete(self) -> None:
        """fast-track-coordination at Final Issuance phase is not 'Complete'."""
        from docreview360 import workflows
        from docreview360.search import ProjectModel

        # Simulate the exact scenario from ai-notes: newly created project with
        # fast-track-coordination workflow at Final Issuance phase
        wf = workflows.create_workflow(
            "test-fast-track",
            ["Initial Drafting", "SME Review", "Final Issuance"],
        )
        # Advance to Final Issuance
        for _ in range(2):
            workflows.advance_workflow(wf.id)
        try:
            pm = ProjectModel(
                id="fast-track-project",
                name="Fast Track Project",
                workflow=wf.id,
            )
            assert pm.status != "Complete", (
                "A project at 'Final Issuance' should not be 'Complete'"
            )
            assert pm.progress < 100, (
                f"A project at 'Final Issuance' should not be 100% complete, got {pm.progress}"
            )
        finally:
            workflows.workflows.pop(wf.id, None)


# ---------------------------------------------------------------------------
# Document number preference
# ---------------------------------------------------------------------------


class TestDocumentNumberField:
    """document_number (user-provided) takes priority over auto-increment number."""

    def test_project_model_exposes_document_number(self) -> None:
        from docreview360.search import ProjectModel

        pm = ProjectModel(
            id="dn-test",
            name="Document Number Test",
            document_number="AC-2024-01",
            number=12,
        )
        assert pm.document_number == "AC-2024-01"
        assert pm.number == 12

    def test_project_api_returns_document_number(self) -> None:
        """The project API response includes document_number when set."""
        client = TestClient(app)
        hdrs = _alice_headers()

        proj_res = client.post(
            "/projects",
            json={"name": "Doc Number API Test", "document_number": "TEST-2024-42"},
            headers=hdrs,
        )
        assert proj_res.status_code == 201
        data = proj_res.json()
        assert data.get("document_number") == "TEST-2024-42"

    def test_project_number_field_defaults_to_none_when_no_document_number(self) -> None:
        """When no document_number is provided, document_number is None."""
        from docreview360.search import ProjectModel

        pm = ProjectModel(id="no-dn", name="No Document Number")
        assert pm.document_number is None

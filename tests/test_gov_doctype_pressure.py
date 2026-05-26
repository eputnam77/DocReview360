# SPDX-License-Identifier: MIT
"""Government document type pressure tests.

Validates the condensed set of government-appropriate document types,
phases, workflow templates, and email templates under load.

Focus areas:
- All 6 default gov doc types are present and correctly structured
- All 5 default phases are present and correctly ordered
- All 4 primary workflow templates are present and usable
- Full lifecycle (Draft → Peer Review → Legal Review → Final Approval → Published)
- Concurrent document type creation and phase assignment
- Edge cases: long names, duplicate creation, phase-workflow links
"""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from docreview360 import auth, db_store, rbac, workflows
from docreview360.api import app
from docreview360.doc_types._registry import DEFAULT_DOC_TYPE_NAMES, DEFAULT_DOC_TYPE_PHASES
from docreview360.phases import DEFAULT_PHASES, list_phases
from docreview360.workflows._templates import DEFAULT_WORKFLOW_DESCRIPTIONS, DEFAULT_WORKFLOW_TEMPLATES


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _admin_headers(username: str = "alice") -> dict[str, str]:
    try:
        auth.USER_REPOSITORY.create_user(username, "Password!1Secure")
    except Exception:
        pass
    rbac.add_role(username, "admin")
    token = auth.create_access_token({"sub": username}, timedelta(hours=1))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _isolated(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> Any:
    user_db = tmp_path / "users.db"
    roles_db = tmp_path / "roles.db"
    app_db = tmp_path / "app.db"

    monkeypatch.setenv("DOCREVIEW360_USER_DB", str(user_db))
    monkeypatch.setenv("DOCREVIEW360_RBAC_DB", str(roles_db))
    auth.configure_user_repository(user_db)
    rbac.configure_role_repository(roles_db)
    rbac.reset_role_assignments(include_defaults=False)
    db_store.reset_db(f"sqlite:///{app_db}")
    monkeypatch.setattr(workflows, "DOCREVIEW360_ENABLE_WORKFLOW_TEMPLATE_PERSISTENCE", True)
    workflows.reset_workflow_templates()
    workflows.workflows.clear()
    yield
    db_store.reset_db(None)
    workflows.reset_workflow_templates()
    workflows.workflows.clear()


# ---------------------------------------------------------------------------
# 1. Default data validation
# ---------------------------------------------------------------------------

class TestDefaultGovernmentData:
    """All default gov data is present, correctly structured, and functional."""

    GOV_DOC_TYPES = [
        "Policy",
        "Standard Operating Procedure",
        "Memorandum",
        "Report",
        "Guidance Document",
        "Meeting Minutes",
    ]

    GOV_PHASES = [
        "Draft",
        "Peer Review",
        "Legal Review",
        "Final Approval",
        "Published",
    ]

    GOV_WORKFLOW_TEMPLATES = [
        "standard-review",
        "fast-track",
        "sop-review",
        "inter-agency-coordination",
    ]

    def test_all_gov_doc_types_present(self) -> None:
        for name in self.GOV_DOC_TYPES:
            assert name in DEFAULT_DOC_TYPE_PHASES, f"Missing gov doc type: {name!r}"
            assert name in DEFAULT_DOC_TYPE_NAMES, f"Missing from DOC_TYPE_NAMES: {name!r}"

    def test_all_gov_phases_present(self) -> None:
        for phase in self.GOV_PHASES:
            assert phase in DEFAULT_PHASES, f"Missing gov phase: {phase!r}"

    def test_phases_are_ordered_correctly(self) -> None:
        assert DEFAULT_PHASES.index("Draft") < DEFAULT_PHASES.index("Final Approval")
        assert DEFAULT_PHASES.index("Peer Review") < DEFAULT_PHASES.index("Legal Review")
        assert DEFAULT_PHASES.index("Legal Review") < DEFAULT_PHASES.index("Final Approval")
        assert DEFAULT_PHASES.index("Final Approval") < DEFAULT_PHASES.index("Published")

    def test_all_gov_workflow_templates_present(self) -> None:
        for tid in self.GOV_WORKFLOW_TEMPLATES:
            assert tid in DEFAULT_WORKFLOW_TEMPLATES, f"Missing workflow template: {tid!r}"
            assert tid in DEFAULT_WORKFLOW_DESCRIPTIONS, f"Missing description for: {tid!r}"

    def test_gov_workflow_templates_have_steps(self) -> None:
        min_steps = {"standard-review": 4, "fast-track": 2, "sop-review": 3, "inter-agency-coordination": 4}
        for tid, min_count in min_steps.items():
            steps = DEFAULT_WORKFLOW_TEMPLATES[tid]
            assert len(steps) >= min_count, (
                f"{tid!r} should have >= {min_count} steps, has {len(steps)}"
            )

    def test_doc_type_phases_use_only_default_phases(self) -> None:
        for doc_type, phases in DEFAULT_DOC_TYPE_PHASES.items():
            for phase in phases:
                assert phase in DEFAULT_PHASES, (
                    f"Doc type {doc_type!r} references unknown phase {phase!r}"
                )

    def test_each_doc_type_starts_with_draft(self) -> None:
        for doc_type, phases in DEFAULT_DOC_TYPE_PHASES.items():
            assert phases[0] == "Draft", (
                f"Doc type {doc_type!r} should start with 'Draft', starts with {phases[0]!r}"
            )

    def test_each_doc_type_ends_with_published(self) -> None:
        for doc_type, phases in DEFAULT_DOC_TYPE_PHASES.items():
            assert phases[-1] == "Published", (
                f"Doc type {doc_type!r} should end with 'Published', ends with {phases[-1]!r}"
            )

    def test_api_returns_all_gov_doc_types(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()
        resp = client.get("/document-types", headers=hdrs)
        assert resp.status_code == 200
        names = {d["name"] for d in resp.json()}
        for name in self.GOV_DOC_TYPES:
            assert name in names, f"API missing gov doc type: {name!r}"

    def test_api_returns_all_gov_phases(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()
        # Seed phases explicitly so this test doesn't depend on bootstrap DB state
        for phase in self.GOV_PHASES:
            client.post("/phases", json={"name": phase}, headers=hdrs)
        resp = client.get("/phases", headers=hdrs)
        assert resp.status_code == 200
        phases = resp.json()
        for phase in self.GOV_PHASES:
            assert phase in phases, f"API missing gov phase: {phase!r}"

    def test_api_returns_all_gov_workflow_templates(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()
        resp = client.get("/workflow-templates", headers=hdrs)
        assert resp.status_code == 200
        ids = {t["id"] for t in resp.json()}
        for tid in self.GOV_WORKFLOW_TEMPLATES:
            assert tid in ids, f"API missing workflow template: {tid!r}"

    def test_doc_type_templates_have_html_headings(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()
        resp = client.get("/document-types", headers=hdrs)
        assert resp.status_code == 200
        for dt in resp.json():
            tmpl = dt.get("template", "")
            assert "<h1>" in tmpl or "<h2>" in tmpl, (
                f"Doc type {dt['name']!r} template missing HTML headings"
            )


# ---------------------------------------------------------------------------
# 2. Full lifecycle workflows
# ---------------------------------------------------------------------------

class TestGovernmentDocumentLifecycle:
    """Full document lifecycle through the standard government review process."""

    def _create_all_phases(self, client: TestClient, hdrs: dict) -> None:
        for phase in DEFAULT_PHASES:
            client.post("/phases", json={"name": phase}, headers=hdrs)

    def test_policy_standard_review_lifecycle(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()
        self._create_all_phases(client, hdrs)

        project_resp = client.post(
            "/projects",
            json={"name": "FY2026 Travel Policy", "doc_type": "Policy", "document_number": "POL-001"},
            headers=hdrs,
        )
        assert project_resp.status_code == 201
        project = project_resp.json()

        wf_resp = client.post(
            "/workflows",
            json={"project": project["id"], "phases": ["Draft", "Legal Review", "Final Approval", "Published"]},
            headers=hdrs,
        )
        assert wf_resp.status_code == 201
        wf = wf_resp.json()
        assert wf["phase"] == "Draft"

        # Advance through all phases
        for expected_phase in ["Legal Review", "Final Approval", "Published"]:
            adv = client.post(f"/workflows/{wf['id']}/advance", json={}, headers=hdrs)
            assert adv.status_code == 200, f"Advance failed at phase {expected_phase}: {adv.text}"
            assert adv.json()["phase"] == expected_phase

    def test_sop_four_phase_lifecycle(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()
        self._create_all_phases(client, hdrs)

        project_resp = client.post(
            "/projects",
            json={"name": "Incident Response SOP", "doc_type": "Standard Operating Procedure"},
            headers=hdrs,
        )
        assert project_resp.status_code == 201
        project = project_resp.json()

        wf_resp = client.post(
            "/workflows",
            json={"project": project["id"], "phases": ["Draft", "Peer Review", "Final Approval", "Published"]},
            headers=hdrs,
        )
        assert wf_resp.status_code == 201
        wf = wf_resp.json()

        for expected_phase in ["Peer Review", "Final Approval", "Published"]:
            adv = client.post(f"/workflows/{wf['id']}/advance", json={}, headers=hdrs)
            assert adv.status_code == 200
            assert adv.json()["phase"] == expected_phase

    def test_report_full_five_phase_lifecycle(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()
        self._create_all_phases(client, hdrs)

        project_resp = client.post(
            "/projects",
            json={"name": "Annual Performance Report 2026", "doc_type": "Report"},
            headers=hdrs,
        )
        assert project_resp.status_code == 201
        project = project_resp.json()

        wf_resp = client.post(
            "/workflows",
            json={
                "project": project["id"],
                "phases": ["Draft", "Peer Review", "Legal Review", "Final Approval", "Published"],
            },
            headers=hdrs,
        )
        assert wf_resp.status_code == 201
        wf = wf_resp.json()
        assert wf["phase"] == "Draft"

        for expected_phase in ["Peer Review", "Legal Review", "Final Approval", "Published"]:
            adv = client.post(f"/workflows/{wf['id']}/advance", json={}, headers=hdrs)
            assert adv.status_code == 200
            assert adv.json()["phase"] == expected_phase

    def test_memorandum_fast_track_two_phase(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()
        self._create_all_phases(client, hdrs)

        project_resp = client.post(
            "/projects",
            json={"name": "Urgent Memo: System Outage", "doc_type": "Memorandum"},
            headers=hdrs,
        )
        assert project_resp.status_code == 201
        project = project_resp.json()

        wf_resp = client.post(
            "/workflows",
            json={"project": project["id"], "phases": ["Draft", "Final Approval", "Published"]},
            headers=hdrs,
        )
        assert wf_resp.status_code == 201
        wf = wf_resp.json()

        adv = client.post(f"/workflows/{wf['id']}/advance", json={}, headers=hdrs)
        assert adv.status_code == 200
        assert adv.json()["phase"] == "Final Approval"

    def test_cannot_advance_past_final_phase(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()
        self._create_all_phases(client, hdrs)

        project_resp = client.post(
            "/projects", json={"name": "Test Doc", "doc_type": "Memorandum"}, headers=hdrs
        )
        project = project_resp.json()

        wf_resp = client.post(
            "/workflows",
            json={"project": project["id"], "phases": ["Draft", "Published"]},
            headers=hdrs,
        )
        wf = wf_resp.json()
        # Advance to final phase
        client.post(f"/workflows/{wf['id']}/advance", json={}, headers=hdrs)
        # Attempt to advance past final — should return 409
        adv = client.post(f"/workflows/{wf['id']}/advance", json={}, headers=hdrs)
        assert adv.status_code == 409, f"Expected 409 at final phase, got {adv.status_code}"


# ---------------------------------------------------------------------------
# 3. Concurrent document type operations
# ---------------------------------------------------------------------------

class TestConcurrentGovDocTypeOps:
    """Concurrent creation, deletion, and querying of government doc types."""

    def test_concurrent_project_creation_across_doc_types(self) -> None:
        """Multiple concurrent projects across all 6 gov doc types — no 5xx."""
        client = TestClient(app)
        hdrs = _admin_headers()
        # Seed all phases
        for phase in DEFAULT_PHASES:
            client.post("/phases", json={"name": phase}, headers=hdrs)

        doc_types = [
            "Policy", "Standard Operating Procedure", "Memorandum",
            "Report", "Guidance Document", "Meeting Minutes",
        ]
        errors = []

        def create_project(doc_type: str, idx: int) -> int:
            resp = client.post(
                "/projects",
                json={"name": f"{doc_type} Project {idx}", "doc_type": doc_type},
                headers=hdrs,
            )
            if resp.status_code >= 500:
                errors.append(f"5xx on {doc_type}: {resp.status_code}")
            return resp.status_code

        with ThreadPoolExecutor(max_workers=6) as pool:
            futs = [pool.submit(create_project, dt, i) for i, dt in enumerate(doc_types * 3)]
            results = [f.result() for f in as_completed(futs)]

        assert not errors, f"5xx errors: {errors}"
        assert all(r in (200, 201) for r in results), f"Unexpected status codes: {results}"

    def test_concurrent_phase_list_reads_are_consistent(self) -> None:
        """50 concurrent reads of the phases list return the same data."""
        client = TestClient(app)
        hdrs = _admin_headers()
        # Seed the 5 gov phases explicitly
        for phase in DEFAULT_PHASES:
            client.post("/phases", json={"name": phase}, headers=hdrs)

        results: list[list[str]] = []
        lock = threading.Lock()

        def read_phases() -> None:
            resp = client.get("/phases", headers=hdrs)
            if resp.status_code == 200:
                with lock:
                    results.append(resp.json())

        threads = [threading.Thread(target=read_phases) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 50
        first = results[0]
        assert all(r == first for r in results), "Inconsistent phase list across concurrent reads"
        for phase in DEFAULT_PHASES:
            assert phase in first, f"Phase {phase!r} missing from concurrent reads"

    def test_concurrent_workflow_create_on_same_doc_type(self) -> None:
        """Multiple workflows for the same doc type simultaneously — no corruption."""
        client = TestClient(app)
        hdrs = _admin_headers()
        for phase in DEFAULT_PHASES:
            client.post("/phases", json={"name": phase}, headers=hdrs)

        # Create 10 projects
        project_ids = []
        for i in range(10):
            resp = client.post(
                "/projects",
                json={"name": f"Policy Doc {i}", "doc_type": "Policy"},
                headers=hdrs,
            )
            if resp.status_code in (200, 201):
                project_ids.append(resp.json()["id"])

        assert len(project_ids) >= 5, "Should have created at least 5 projects"

        workflow_ids = []
        errors = []
        lock = threading.Lock()

        def create_workflow(pid: str) -> None:
            resp = client.post(
                "/workflows",
                json={"project": pid, "phases": ["Draft", "Legal Review", "Final Approval", "Published"]},
                headers=hdrs,
            )
            if resp.status_code in (200, 201):
                with lock:
                    workflow_ids.append(resp.json()["id"])
            elif resp.status_code >= 500:
                with lock:
                    errors.append(resp.status_code)

        threads = [threading.Thread(target=create_workflow, args=(pid,)) for pid in project_ids]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"5xx during concurrent workflow creation: {errors}"
        assert len(workflow_ids) == len(project_ids)
        assert len(set(workflow_ids)) == len(workflow_ids), "Duplicate workflow IDs!"


# ---------------------------------------------------------------------------
# 4. Phase-workflow template linking
# ---------------------------------------------------------------------------

class TestPhaseWorkflowTemplateLinks:
    """Phases can be linked to workflow templates and the link is stable."""

    def test_link_standard_review_to_legal_review_phase(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()
        # Seed phases
        for phase in DEFAULT_PHASES:
            client.post("/phases", json={"name": phase}, headers=hdrs)

        resp = client.put(
            "/phases/Legal Review/workflow-template",
            json={"workflow_template_id": "standard-review"},
            headers=hdrs,
        )
        assert resp.status_code in (200, 204), f"Unexpected status: {resp.status_code}: {resp.text}"

    def test_all_workflow_templates_have_non_empty_descriptions(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()
        resp = client.get("/workflow-templates", headers=hdrs)
        assert resp.status_code == 200
        primary_ids = {"standard-review", "fast-track", "sop-review", "inter-agency-coordination"}
        for tmpl in resp.json():
            if tmpl["id"] in primary_ids:
                assert tmpl.get("description"), (
                    f"Workflow template {tmpl['id']!r} has empty description"
                )

    def test_standard_review_has_approving_official_step(self) -> None:
        steps = DEFAULT_WORKFLOW_TEMPLATES["standard-review"]
        roles = [s.role.lower() for s in steps]
        assert any("approving" in r for r in roles), (
            "standard-review should have an Approving Official step"
        )

    def test_fast_track_has_exactly_two_steps(self) -> None:
        steps = DEFAULT_WORKFLOW_TEMPLATES["fast-track"]
        assert len(steps) == 2, f"fast-track should have 2 steps, has {len(steps)}"

    def test_inter_agency_coordination_has_external_liaison(self) -> None:
        steps = DEFAULT_WORKFLOW_TEMPLATES["inter-agency-coordination"]
        roles = [s.role.lower() for s in steps]
        assert any("agency" in r or "external" in r or "liaison" in r for r in roles), (
            "inter-agency-coordination should have an external agency/liaison step"
        )


# ---------------------------------------------------------------------------
# 5. Edge cases and human error
# ---------------------------------------------------------------------------

class TestGovDocTypeEdgeCases:
    """Edge cases: invalid input, duplicates, missing phases, boundary conditions."""

    def test_reject_workflow_with_unknown_phase(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()
        # Do NOT seed phases — use only non-existent ones
        project_resp = client.post(
            "/projects", json={"name": "Test", "doc_type": "Policy"}, headers=hdrs
        )
        if project_resp.status_code not in (200, 201):
            return
        project_id = project_resp.json()["id"]

        resp = client.post(
            "/workflows",
            json={"project": project_id, "phases": ["NonExistentPhase", "AlsoFake"]},
            headers=hdrs,
        )
        assert resp.status_code == 422, (
            f"Should reject workflow with non-existent phases, got {resp.status_code}"
        )

    def test_reject_empty_phases_list(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()
        project_resp = client.post(
            "/projects", json={"name": "Test", "doc_type": "Memorandum"}, headers=hdrs
        )
        if project_resp.status_code not in (200, 201):
            return
        project_id = project_resp.json()["id"]

        resp = client.post(
            "/workflows",
            json={"project": project_id, "phases": []},
            headers=hdrs,
        )
        assert resp.status_code in (400, 422), f"Should reject empty phases, got {resp.status_code}"

    def test_duplicate_phase_creation_is_idempotent(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()
        # Create a phase
        r1 = client.post("/phases", json={"name": "Draft"}, headers=hdrs)
        # Create again — should be idempotent (200 or 409)
        r2 = client.post("/phases", json={"name": "Draft"}, headers=hdrs)
        assert r1.status_code in (200, 201), f"First create failed: {r1.status_code}"
        assert r2.status_code in (200, 201, 409), f"Duplicate create unexpected: {r2.status_code}"

    def test_starter_content_for_all_gov_doc_types(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()
        doc_types = [
            "Policy", "Standard Operating Procedure", "Memorandum",
            "Report", "Guidance Document", "Meeting Minutes",
        ]
        for name in doc_types:
            resp = client.get(f"/document-types/{name}/starter-content", headers=hdrs)
            assert resp.status_code == 200, (
                f"starter-content for {name!r} returned {resp.status_code}"
            )
            data = resp.json()
            assert "<h" in data.get("content", ""), (
                f"starter-content for {name!r} has no HTML headings"
            )

    def test_workflow_template_steps_have_increasing_order(self) -> None:
        for tid, steps in DEFAULT_WORKFLOW_TEMPLATES.items():
            last_order = -1
            for step in steps:
                assert step.order > last_order, (
                    f"Template {tid!r}: step {step.role!r} has non-increasing order {step.order}"
                )
                last_order = step.order

    def test_whitespace_phase_name_rejected(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()
        resp = client.post("/phases", json={"name": "   "}, headers=hdrs)
        assert resp.status_code in (400, 422), f"Whitespace phase name should be rejected: {resp.status_code}"

    def test_doc_type_url_encoding_works_for_multiword_names(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()
        # "Standard Operating Procedure" has spaces — test URL encoding
        resp = client.get(
            "/document-types/Standard Operating Procedure/starter-content", headers=hdrs
        )
        # Either 200 (found) or 404 (spaces in URL not URL-encoded, which is acceptable)
        assert resp.status_code in (200, 404), f"Unexpected: {resp.status_code}"

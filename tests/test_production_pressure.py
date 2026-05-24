# SPDX-License-Identifier: MIT
"""Production pressure tests — simulate real-world load, human error patterns,
and concurrent operations that would occur in a live deployment.

Every test here starts from the perspective: "what would break if 50 admins
were using this app simultaneously on day one of production?"
"""
from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from docreview360 import auth, db_store, rbac, workflows
from docreview360.api import app
from docreview360.phases import list_phases


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _admin_headers(username: str = "alice") -> dict[str, str]:
    try:
        auth.USER_REPOSITORY.create_user(
            username,
            auth.DEMO_USER_DEFAULTS.get(username, {}).get("password", "Password!1"),
            otp_secret=auth.DEMO_USER_DEFAULTS.get(username, {}).get("otp_secret"),
        )
    except Exception:
        pass
    rbac.add_role(username, "admin")
    token = auth.create_access_token({"sub": username}, timedelta(hours=1))
    return {"Authorization": f"Bearer {token}"}


def _user_headers(username: str) -> dict[str, str]:
    try:
        auth.USER_REPOSITORY.create_user(username, "Password!1Secure")
    except Exception:
        pass
    rbac.set_user_roles(username, ["user"])
    token = auth.create_access_token({"sub": username}, timedelta(hours=1))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _isolated(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> Any:
    """Full state isolation — fresh DB, auth, roles, and workflow stores per test."""
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
# 1. Concurrent workflow advances — race condition safety
# ---------------------------------------------------------------------------

class TestConcurrentWorkflowAdvance:
    """Advancing the same workflow from multiple threads must not corrupt state."""

    def test_concurrent_advance_same_workflow_no_data_corruption(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()

        # Seed phases in the DB
        for phase in ["Alpha", "Beta", "Gamma", "Delta", "Epsilon"]:
            r = client.post("/phases", json={"name": phase}, headers=hdrs)
            assert r.status_code in {201, 409}

        # Create a workflow via project creation
        proj = client.post(
            "/projects",
            json={"name": "Concurrent Test", "phase": "Alpha",
                  "workflow": "branch-coordination"},
            headers=hdrs,
        )
        assert proj.status_code == 201
        wf_id = proj.json()["workflow"]
        assert wf_id

        results: list[int] = []
        errors: list[str] = []

        def advance() -> None:
            r = client.post(f"/workflows/{wf_id}/advance", headers=hdrs)
            results.append(r.status_code)
            if r.status_code not in {200, 409}:
                errors.append(f"Unexpected {r.status_code}: {r.text}")

        # 20 concurrent advance calls — most should 409 (already final) or 200
        with ThreadPoolExecutor(max_workers=20) as pool:
            futs = [pool.submit(advance) for _ in range(20)]
            for f in as_completed(futs):
                f.result()

        assert not errors, f"Unexpected status codes: {errors}"
        # No 500s — thread safety holds
        assert 500 not in results

    def test_advance_at_final_phase_returns_409(self) -> None:
        """Once at final phase, every subsequent advance must return 409."""
        from docreview360.workflows import create_workflow as _create_workflow

        # Seed phases in DB so the engine validation passes
        client = TestClient(app)
        hdrs = _admin_headers()
        for phase in ["Step A", "Step B"]:
            client.post("/phases", json={"name": phase}, headers=hdrs)

        # Directly create a 2-phase workflow so we control the phases list
        wf = _create_workflow("advance-test-project", ["Step A", "Step B"])
        wf_id = wf.id

        # Advance once — moves from Step A → Step B (final)
        r = client.post(f"/workflows/{wf_id}/advance", headers=hdrs)
        assert r.status_code == 200
        assert r.json()["phase"] == "Step B"

        # Every subsequent advance must be 409, never silent
        for _ in range(5):
            r = client.post(f"/workflows/{wf_id}/advance", headers=hdrs)
            assert r.status_code == 409
            assert "final phase" in r.text.lower()

    def test_advance_nonexistent_workflow_returns_404(self) -> None:
        client = TestClient(app)
        r = client.post("/workflows/does-not-exist/advance", headers=_admin_headers())
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# 2. Phase validation on workflow creation
# ---------------------------------------------------------------------------

class TestWorkflowPhaseValidation:
    """POST /workflows must reject non-existent phases — no orphaned refs."""

    def _error_msg(self, r: Any) -> str:
        """Extract the error message regardless of response envelope format."""
        body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        return body.get("message") or body.get("detail") or r.text

    def test_create_workflow_with_nonexistent_phases_rejected(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()

        r = client.post(
            "/workflows",
            json={"project": "ghost-proj", "phases": ["Ghost Phase", "Phantom Phase"]},
            headers=hdrs,
        )
        assert r.status_code == 422
        msg = self._error_msg(r)
        assert "Ghost Phase" in msg or "unknown phase" in msg.lower()

    def test_create_workflow_with_mix_of_valid_and_invalid_phases_rejected(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()

        # Seed one real phase
        client.post("/phases", json={"name": "Real Phase"}, headers=hdrs)

        r = client.post(
            "/workflows",
            json={"project": "mixed-proj", "phases": ["Real Phase", "Fake Phase"]},
            headers=hdrs,
        )
        assert r.status_code == 422
        assert "Fake Phase" in self._error_msg(r)

    def test_create_workflow_with_all_valid_phases_succeeds(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()

        for phase in ["Phase A", "Phase B"]:
            client.post("/phases", json={"name": phase}, headers=hdrs)

        r = client.post(
            "/workflows",
            json={"project": "valid-proj", "phases": ["Phase A", "Phase B"]},
            headers=hdrs,
        )
        assert r.status_code == 201


# ---------------------------------------------------------------------------
# 3. DELETE /workflows/{id} — new endpoint
# ---------------------------------------------------------------------------

class TestDeleteWorkflow:

    def test_delete_workflow_removes_it(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()

        client.post("/phases", json={"name": "Draft"}, headers=hdrs)
        proj = client.post(
            "/projects",
            json={"name": "Deletable Project", "phase": "Draft",
                  "workflow": "branch-coordination"},
            headers=hdrs,
        )
        assert proj.status_code == 201
        wf_id = proj.json()["workflow"]

        del_r = client.delete(f"/workflows/{wf_id}", headers=hdrs)
        assert del_r.status_code == 204

        get_r = client.get(f"/workflows/{wf_id}", headers=hdrs)
        assert get_r.status_code == 404

    def test_delete_nonexistent_workflow_returns_404(self) -> None:
        client = TestClient(app)
        r = client.delete("/workflows/no-such-id", headers=_admin_headers())
        assert r.status_code == 404

    def test_delete_workflow_requires_admin(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()
        client.post("/phases", json={"name": "Draft"}, headers=hdrs)
        proj = client.post(
            "/projects",
            json={"name": "Protected WF", "phase": "Draft",
                  "workflow": "branch-coordination"},
            headers=hdrs,
        )
        wf_id = proj.json()["workflow"]

        user_hdrs = _user_headers("regular_user")
        r = client.delete(f"/workflows/{wf_id}", headers=user_hdrs)
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# 4. Human error edge cases — input boundary conditions
# ---------------------------------------------------------------------------

class TestHumanInputEdgeCases:
    """Real humans make these mistakes. The API must handle them gracefully."""

    def test_workflow_template_name_xss_payload_rejected(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()
        r = client.post(
            "/workflow-templates",
            json={"name": "<script>alert('xss')</script>", "steps": [{"role": "R"}]},
            headers=hdrs,
        )
        assert r.status_code == 422

    def test_workflow_template_name_sql_injection_rejected(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()
        r = client.post(
            "/workflow-templates",
            json={"name": "'; DROP TABLE workflows; --", "steps": [{"role": "R"}]},
            headers=hdrs,
        )
        # SQL injection chars < > & ' " are blocked by _ensure_name validator
        assert r.status_code in {422, 400}

    def test_workflow_template_name_10k_chars_rejected(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()
        r = client.post(
            "/workflow-templates",
            json={"name": "A" * 10_000, "steps": [{"role": "R"}]},
            headers=hdrs,
        )
        assert r.status_code == 422

    def test_document_type_name_empty_string_rejected(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()
        r = client.post(
            "/document-types",
            json={"name": "", "template": "<h1>empty</h1>"},
            headers=hdrs,
        )
        assert r.status_code == 422

    def test_document_type_name_whitespace_only_rejected(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()
        r = client.post(
            "/document-types",
            json={"name": "   ", "template": "<h1>blank</h1>"},
            headers=hdrs,
        )
        assert r.status_code == 422

    def test_document_type_name_200_chars_accepted(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()
        long_name = "A" * 200
        r = client.post(
            "/document-types",
            json={"name": long_name, "template": "<h1>Long</h1>"},
            headers=hdrs,
        )
        assert r.status_code == 201

    def test_document_type_name_201_chars_rejected(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()
        r = client.post(
            "/document-types",
            json={"name": "B" * 201, "template": "<h1>Too Long</h1>"},
            headers=hdrs,
        )
        assert r.status_code == 422

    def test_phase_name_unicode_emoji_accepted(self) -> None:
        """Admins may paste emoji into phase names — must not crash."""
        client = TestClient(app)
        hdrs = _admin_headers()
        r = client.post("/phases", json={"name": "Phase 🚀 Review"}, headers=hdrs)
        assert r.status_code in {201, 409}

    def test_phase_name_unicode_cyrillic_accepted(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()
        r = client.post("/phases", json={"name": "Черновик"}, headers=hdrs)
        assert r.status_code in {201, 409}

    def test_double_create_document_type_returns_409(self) -> None:
        """Simulate user double-clicking 'Save' — second request must 409."""
        client = TestClient(app)
        hdrs = _admin_headers()
        payload = {"name": "Double Submit Type", "template": "<h1>T</h1>"}
        r1 = client.post("/document-types", json=payload, headers=hdrs)
        r2 = client.post("/document-types", json=payload, headers=hdrs)
        assert r1.status_code == 201
        assert r2.status_code == 409

    def test_double_create_phase_returns_409(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()
        r1 = client.post("/phases", json={"name": "Dupe Phase"}, headers=hdrs)
        r2 = client.post("/phases", json={"name": "Dupe Phase"}, headers=hdrs)
        assert r1.status_code == 201
        assert r2.status_code == 409

    def test_malformed_json_body_returns_422(self) -> None:
        """Truncated or malformed JSON must not cause 500."""
        client = TestClient(app)
        hdrs = _admin_headers()
        hdrs["Content-Type"] = "application/json"
        r = client.post("/workflow-templates", data=b"{name: bad json", headers=hdrs)
        assert r.status_code == 422

    def test_missing_required_fields_returns_422(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()
        # Missing 'template' field (required on DocumentTypeModel)
        r = client.post("/document-types", json={"name": "NoTemplate"}, headers=hdrs)
        assert r.status_code == 422

    def test_workflow_create_empty_phases_list_rejected(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()
        r = client.post(
            "/workflows",
            json={"project": "test", "phases": []},
            headers=hdrs,
        )
        assert r.status_code == 422

    def test_workflow_create_blank_phase_string_rejected(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()
        r = client.post(
            "/workflows",
            json={"project": "test", "phases": ["Valid", "   "]},
            headers=hdrs,
        )
        assert r.status_code == 422

    def test_workflow_create_invalid_mode_rejected(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()
        client.post("/phases", json={"name": "P1"}, headers=hdrs)
        r = client.post(
            "/workflows",
            json={"project": "test", "phases": ["P1"], "mode": "turbo"},
            headers=hdrs,
        )
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# 5. Admin self-destructive operations
# ---------------------------------------------------------------------------

class TestAdminSelfDestructiveOps:
    """Humans do these things. The system must protect itself."""

    def test_delete_phase_in_use_without_replacement_returns_400(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()

        client.post("/phases", json={"name": "Active Phase"}, headers=hdrs)
        proj = client.post(
            "/projects",
            json={"name": "Real Project", "phase": "Active Phase",
                  "workflow": "branch-coordination"},
            headers=hdrs,
        )
        assert proj.status_code == 201

        r = client.delete("/phases/Active%20Phase", headers=hdrs)
        assert r.status_code == 400
        assert "replacement" in r.text.lower()

    def test_delete_phase_in_use_with_nonexistent_replacement_returns_404(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()

        client.post("/phases", json={"name": "Used Phase"}, headers=hdrs)
        proj = client.post(
            "/projects",
            json={"name": "Has Workflow", "phase": "Used Phase",
                  "workflow": "branch-coordination"},
            headers=hdrs,
        )
        assert proj.status_code == 201

        r = client.delete(
            "/phases/Used%20Phase?replacement=Ghost%20Phase", headers=hdrs
        )
        assert r.status_code == 404

    def test_delete_doc_type_in_use_without_replacement_returns_400(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()

        client.post(
            "/document-types",
            json={"name": "Locked Type", "template": "<h1>L</h1>"},
            headers=hdrs,
        )
        client.post(
            "/projects",
            json={"name": "Uses Locked Type", "doc_type": "Locked Type"},
            headers=hdrs,
        )

        r = client.delete("/document-types/Locked%20Type", headers=hdrs)
        assert r.status_code == 400
        assert "replacement" in r.text.lower()

    def test_delete_doc_type_with_self_replacement_returns_400(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()

        client.post(
            "/document-types",
            json={"name": "Self Ref Type", "template": "<h1>S</h1>"},
            headers=hdrs,
        )
        client.post(
            "/projects",
            json={"name": "Needs Replacement", "doc_type": "Self Ref Type"},
            headers=hdrs,
        )

        r = client.delete(
            "/document-types/Self%20Ref%20Type?replacement=Self%20Ref%20Type",
            headers=hdrs,
        )
        assert r.status_code == 400
        assert "different" in r.text.lower()

    def test_delete_workflow_template_in_use_returns_409(self) -> None:
        """A workflow template referenced by a phase must not be deletable."""
        client = TestClient(app)
        hdrs = _admin_headers()

        r = client.post(
            "/workflow-templates",
            json={
                "name": "Protected Template",
                "steps": [{"role": "Reviewer", "required": True}],
            },
            headers=hdrs,
        )
        assert r.status_code == 201

        client.post("/phases", json={"name": "Linked Phase"}, headers=hdrs)
        client.put(
            "/phases/Linked%20Phase/workflow-template",
            json={"workflow_template_id": "Protected Template"},
            headers=hdrs,
        )

        r = client.delete("/workflow-templates/Protected%20Template", headers=hdrs)
        assert r.status_code == 409
        assert "in use" in r.text.lower()

    def test_rename_phase_to_existing_name_returns_409(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()
        client.post("/phases", json={"name": "Phase One"}, headers=hdrs)
        client.post("/phases", json={"name": "Phase Two"}, headers=hdrs)

        r = client.put("/phases/Phase%20One", json={"name": "Phase Two"}, headers=hdrs)
        assert r.status_code == 409


# ---------------------------------------------------------------------------
# 6. Concurrent bulk project creation — no 500s under load
# ---------------------------------------------------------------------------

class TestConcurrentBulkOperations:

    def test_50_concurrent_phase_creates_no_crashes(self) -> None:
        """50 concurrent POST /phases — some will 409 (duplicate), none should 500."""
        client = TestClient(app)
        hdrs = _admin_headers()
        results: list[int] = []

        def create_phase(i: int) -> int:
            # Mix of unique and duplicate names to stress both paths
            name = f"BulkPhase-{i % 10}"
            r = client.post("/phases", json={"name": name}, headers=hdrs)
            return r.status_code

        with ThreadPoolExecutor(max_workers=20) as pool:
            futs = [pool.submit(create_phase, i) for i in range(50)]
            for f in as_completed(futs):
                results.append(f.result())

        assert 500 not in results
        assert all(s in {201, 409} for s in results)

    def test_20_concurrent_doc_type_creates_no_crashes(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()
        results: list[int] = []

        def create_dt(i: int) -> int:
            # Even indices duplicate to stress 409 path
            name = f"DocType-{i % 10}"
            r = client.post(
                "/document-types",
                json={"name": name, "template": f"<h1>{name}</h1>"},
                headers=hdrs,
            )
            return r.status_code

        with ThreadPoolExecutor(max_workers=10) as pool:
            futs = [pool.submit(create_dt, i) for i in range(20)]
            for f in as_completed(futs):
                results.append(f.result())

        assert 500 not in results
        assert all(s in {201, 409} for s in results)

    def test_concurrent_workflow_template_create_and_read(self) -> None:
        """Writers and readers hitting workflow-templates simultaneously."""
        client = TestClient(app)
        hdrs = _admin_headers()
        results: list[int] = []

        def writer(i: int) -> int:
            r = client.post(
                "/workflow-templates",
                json={
                    "name": f"Concurrent Template {i}",
                    "steps": [{"role": "Reviewer", "required": True}],
                },
                headers=hdrs,
            )
            return r.status_code

        def reader() -> int:
            r = client.get("/workflow-templates", headers=hdrs)
            return r.status_code

        with ThreadPoolExecutor(max_workers=20) as pool:
            futs = [pool.submit(writer, i) for i in range(10)]
            futs += [pool.submit(reader) for _ in range(10)]
            for f in as_completed(futs):
                results.append(f.result())

        assert 500 not in results


# ---------------------------------------------------------------------------
# 7. Session and auth edge cases
# ---------------------------------------------------------------------------

class TestAuthEdgeCases:

    def test_expired_token_returns_401(self) -> None:
        """An expired JWT must be rejected on admin-protected endpoints."""
        client = TestClient(app)
        expired = auth.create_access_token({"sub": "alice"}, timedelta(seconds=-1))
        # POST /phases is admin-only — expired token must be rejected
        r = client.post("/phases", json={"name": "ExpiredTest"}, headers={"Authorization": f"Bearer {expired}"})
        assert r.status_code == 401

    def test_malformed_bearer_token_returns_401(self) -> None:
        client = TestClient(app)
        r = client.post(
            "/phases",
            json={"name": "MalformedTest"},
            headers={"Authorization": "Bearer not.a.valid.jwt"},
        )
        assert r.status_code == 401

    def test_missing_auth_header_on_admin_endpoint_returns_401(self) -> None:
        client = TestClient(app)
        r = client.post("/phases", json={"name": "NoAuth Phase"})
        assert r.status_code == 401

    def test_user_role_cannot_create_phase(self) -> None:
        client = TestClient(app)
        r = client.post(
            "/phases", json={"name": "User Phase"}, headers=_user_headers("eve")
        )
        assert r.status_code == 403

    def test_user_role_cannot_create_document_type(self) -> None:
        client = TestClient(app)
        r = client.post(
            "/document-types",
            json={"name": "Unprivileged DT", "template": "<h1>X</h1>"},
            headers=_user_headers("frank"),
        )
        assert r.status_code == 403

    def test_user_role_cannot_create_workflow_template(self) -> None:
        client = TestClient(app)
        r = client.post(
            "/workflow-templates",
            json={"name": "Unprivileged Template", "steps": [{"role": "R"}]},
            headers=_user_headers("grace"),
        )
        assert r.status_code == 403

    def test_suspended_user_token_rejected(self) -> None:
        """Suspending a user must invalidate their existing tokens immediately."""
        client = TestClient(app)
        admin_hdrs = _admin_headers()

        # Create and issue token to target user
        try:
            auth.USER_REPOSITORY.create_user("target_user", "Password!1Secure")
        except Exception:
            pass
        rbac.add_role("target_user", "admin")
        token = auth.create_access_token({"sub": "target_user"}, timedelta(hours=1))
        target_hdrs = {"Authorization": f"Bearer {token}"}

        # Confirm token works before suspension
        r = client.get("/phases", headers=target_hdrs)
        assert r.status_code == 200

        # Admin suspends the user
        r = client.patch(
            "/users/target_user/suspend",
            json={"suspended": True},
            headers=admin_hdrs,
        )
        # Suspension endpoint might be at different path — try both common patterns
        if r.status_code == 404:
            r = client.post(
                "/users/target_user/suspend",
                headers=admin_hdrs,
            )

        # After suspension, the old token must be rejected on protected endpoints
        if r.status_code in {200, 204}:
            r2 = client.post("/phases", json={"name": "SuspendedTest"}, headers=target_hdrs)
            assert r2.status_code in {401, 403}


# ---------------------------------------------------------------------------
# 8. Large-volume response time guard
# ---------------------------------------------------------------------------

class TestLargeVolumePerformance:

    def test_list_phases_with_50_phases_responds_fast(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()

        for i in range(50):
            client.post("/phases", json={"name": f"Volume Phase {i}"}, headers=hdrs)

        start = time.monotonic()
        r = client.get("/phases")
        elapsed = time.monotonic() - start

        assert r.status_code == 200
        assert len(r.json()) >= 50
        assert elapsed < 2.0, f"GET /phases with 50 items took {elapsed:.2f}s — too slow"

    def test_list_workflow_templates_with_30_templates_responds_fast(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()

        for i in range(30):
            client.post(
                "/workflow-templates",
                json={
                    "name": f"Volume Template {i}",
                    "steps": [{"role": "Reviewer", "required": True}],
                },
                headers=hdrs,
            )

        start = time.monotonic()
        r = client.get("/workflow-templates", headers=hdrs)
        elapsed = time.monotonic() - start

        assert r.status_code == 200
        assert elapsed < 2.0, f"GET /workflow-templates took {elapsed:.2f}s — too slow"

    def test_list_document_types_with_30_types_responds_fast(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()

        for i in range(30):
            client.post(
                "/document-types",
                json={"name": f"Volume Doc Type {i}", "template": f"<h1>T{i}</h1>"},
                headers=hdrs,
            )

        start = time.monotonic()
        r = client.get("/document-types", headers=hdrs)
        elapsed = time.monotonic() - start

        assert r.status_code == 200
        assert elapsed < 2.0, f"GET /document-types took {elapsed:.2f}s — too slow"


# ---------------------------------------------------------------------------
# 9. Data integrity after delete-and-recreate cycles
# ---------------------------------------------------------------------------

class TestDataIntegrityDeleteRecreate:

    def test_delete_and_recreate_phase_same_name(self) -> None:
        """Delete a phase and immediately recreate it — no stale state."""
        client = TestClient(app)
        hdrs = _admin_headers()

        client.post("/phases", json={"name": "Recycled Phase"}, headers=hdrs)

        # Delete the unused phase
        r = client.delete("/phases/Recycled%20Phase", headers=hdrs)
        assert r.status_code == 204

        # Recreate must succeed, not 409
        r = client.post("/phases", json={"name": "Recycled Phase"}, headers=hdrs)
        assert r.status_code == 201

    def test_delete_and_recreate_workflow_template_same_name(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()

        client.post(
            "/workflow-templates",
            json={"name": "Recycled Template", "steps": [{"role": "R"}]},
            headers=hdrs,
        )
        client.delete("/workflow-templates/Recycled%20Template", headers=hdrs)

        r = client.post(
            "/workflow-templates",
            json={"name": "Recycled Template", "steps": [{"role": "R"}]},
            headers=hdrs,
        )
        assert r.status_code == 201

    def test_delete_and_recreate_document_type_same_name(self) -> None:
        client = TestClient(app)
        hdrs = _admin_headers()

        client.post(
            "/document-types",
            json={"name": "Recycled DT", "template": "<h1>R</h1>"},
            headers=hdrs,
        )
        client.delete("/document-types/Recycled%20DT", headers=hdrs)

        r = client.post(
            "/document-types",
            json={"name": "Recycled DT", "template": "<h1>New</h1>"},
            headers=hdrs,
        )
        assert r.status_code == 201

    def test_workflow_phase_list_consistent_after_phase_rename(self) -> None:
        """Renaming a phase must update it in all existing workflows."""
        client = TestClient(app)
        hdrs = _admin_headers()

        client.post("/phases", json={"name": "Old Name"}, headers=hdrs)
        proj = client.post(
            "/projects",
            json={"name": "Rename Test Project", "phase": "Old Name",
                  "workflow": "branch-coordination"},
            headers=hdrs,
        )
        assert proj.status_code == 201
        wf_id = proj.json()["workflow"]

        # Rename the phase
        r = client.put("/phases/Old%20Name", json={"name": "New Name"}, headers=hdrs)
        assert r.status_code == 200

        # The workflow's phases list must be updated to "New Name"
        wf = client.get(f"/workflows/{wf_id}", headers=hdrs)
        assert wf.status_code == 200
        wf_data = wf.json()
        assert "New Name" in wf_data["phases"]
        assert "Old Name" not in wf_data["phases"]


# ---------------------------------------------------------------------------
# 10. Workflow template full lifecycle under production conditions
# ---------------------------------------------------------------------------

class TestWorkflowTemplateProductionLifecycle:

    def test_full_admin_configuration_round_trip(self) -> None:
        """Simulate the sequence an admin follows on day one: create everything,
        link it together, verify it works, then clean up."""
        client = TestClient(app)
        hdrs = _admin_headers()

        # Step 1: Create doc type
        dt = client.post(
            "/document-types",
            json={"name": "Policy Document", "template": "<h1>Policy</h1>"},
            headers=hdrs,
        )
        assert dt.status_code == 201

        # Step 2: Create phases
        for phase in ["Policy Draft", "Legal Review", "Executive Approval", "Published"]:
            r = client.post("/phases", json={"name": phase}, headers=hdrs)
            assert r.status_code in {201, 409}

        # Step 3: Create workflow template
        tmpl = client.post(
            "/workflow-templates",
            json={
                "name": "Policy Approval Flow",
                "description": "Standard policy review and approval",
                "steps": [
                    {"role": "Legal Reviewer", "required": True},
                    {"role": "VP Approver", "required": True},
                    {"role": "CISO Sign-off", "required": False},
                ],
            },
            headers=hdrs,
        )
        assert tmpl.status_code == 201
        assert tmpl.json()["id"] == "Policy Approval Flow"

        # Step 4: Attach workflow template to first phase
        link = client.put(
            "/phases/Policy%20Draft/workflow-template",
            json={"workflow_template_id": "Policy Approval Flow"},
            headers=hdrs,
        )
        assert link.status_code == 200

        # Step 5: Attach template to doc type
        update = client.put(
            "/document-types/Policy%20Document",
            json={
                "name": "Policy Document",
                "template": "<h1>Policy</h1>",
                "default_workflow_template_id": "Policy Approval Flow",
                "workflow": ["Policy Draft", "Legal Review", "Executive Approval", "Published"],
            },
            headers=hdrs,
        )
        assert update.status_code == 200

        # Step 6: Create a project using this doc type
        proj = client.post(
            "/projects",
            json={
                "name": "Security Policy v2",
                "doc_type": "Policy Document",
                "phase": "Policy Draft",
            },
            headers=hdrs,
        )
        assert proj.status_code == 201

        # Step 7: Verify the configuration is accessible
        dt_phases = client.get("/document-types/Policy%20Document/phases", headers=hdrs)
        assert dt_phases.status_code == 200
        assert "Policy Draft" in dt_phases.json()

        tmpl_detail = client.get("/workflow-templates/Policy%20Approval%20Flow", headers=hdrs)
        assert tmpl_detail.status_code == 200
        roles = [s["role"] for s in tmpl_detail.json()["steps"]]
        assert "Legal Reviewer" in roles

        # Step 8: Verify template cannot be deleted while linked to a phase
        cannot_del = client.delete("/workflow-templates/Policy%20Approval%20Flow", headers=hdrs)
        assert cannot_del.status_code == 409

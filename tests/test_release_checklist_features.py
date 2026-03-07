"""Tests for features added in the release checklist implementation round.

Covers:
- Viewer-only project role in RBAC
- Role-based permission matrix visualization endpoint
- Phase-based audit snapshots (module + API)
- Exportable audit package (JSON) endpoint
- Executive summary dashboard endpoint
- Per-phase SLA tracking (module + API)
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from docreview360 import auth, rbac
from docreview360.api import app
from docreview360.audit import clear_audit_log, log_audit_event
from docreview360.audit_snapshots import capture_phase_snapshot, get_phase_snapshots
from docreview360.documents import import_document
from docreview360.phase_sla import (
    clear_sla_store,
    delete_phase_sla,
    evaluate_phase_sla,
    get_all_phase_slas,
    get_phase_sla,
    set_phase_sla,
)
from docreview360.reporting import executive_summary


def _alice_headers() -> dict[str, str]:
    """Return Authorization headers for the demo admin user."""
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
# Viewer role
# ---------------------------------------------------------------------------


def test_viewer_role_exists_in_default_permissions() -> None:
    """The 'viewer' role must be present in the default RBAC permissions map."""
    defaults = rbac._DEFAULT_ROLE_PERMISSIONS
    assert "viewer" in defaults, "viewer role missing from _DEFAULT_ROLE_PERMISSIONS"


def test_viewer_role_has_only_read_permission() -> None:
    """The viewer role should grant only 'read' access."""
    rbac.reload_role_permissions(force=True)
    perms = rbac.get_role_permissions()
    assert "viewer" in perms
    assert perms["viewer"] == {"read"}


def test_viewer_role_grants_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A user with the viewer role can perform read operations."""
    import os

    orig_path = os.environ.get("DOCREVIEW360_RBAC_DB", "")
    try:
        rbac.configure_role_repository(tmp_path / "roles_viewer.db")
        rbac.reset_role_assignments(include_defaults=False)
        rbac.set_user_roles("carol_viewer", ["viewer"])
        assert rbac.has_permission("carol_viewer", "read")
        assert not rbac.has_permission("carol_viewer", "create")
        assert not rbac.has_permission("carol_viewer", "update")
        assert not rbac.has_permission("carol_viewer", "delete")
    finally:
        # Restore the default RBAC store so subsequent tests use the right DB.
        if orig_path:
            rbac.configure_role_repository(orig_path)
        else:
            from pathlib import Path as _Path

            rbac.configure_role_repository(_Path("docreview360_roles.db").resolve())


# ---------------------------------------------------------------------------
# RBAC permission matrix endpoint
# ---------------------------------------------------------------------------


def test_rbac_matrix_endpoint_returns_structure() -> None:
    client = TestClient(app)
    resp = client.get("/rbac/matrix", headers=_alice_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert "roles" in data
    assert "permissions" in data
    assert "matrix" in data
    assert "total_roles" in data
    assert "total_permissions" in data


def test_rbac_matrix_contains_viewer_role() -> None:
    client = TestClient(app)
    resp = client.get("/rbac/matrix", headers=_alice_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert "viewer" in data["roles"]


def test_rbac_matrix_viewer_read_is_true() -> None:
    client = TestClient(app)
    resp = client.get("/rbac/matrix", headers=_alice_headers())
    assert resp.status_code == 200
    data = resp.json()
    matrix = data["matrix"]
    assert "viewer" in matrix
    assert matrix["viewer"].get("read") is True


def test_rbac_matrix_totals_consistent() -> None:
    client = TestClient(app)
    resp = client.get("/rbac/matrix", headers=_alice_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_roles"] == len(data["roles"])
    assert data["total_permissions"] == len(data["permissions"])


def test_rbac_matrix_all_cells_are_bool() -> None:
    """Every cell in the matrix must be a boolean."""
    client = TestClient(app)
    resp = client.get("/rbac/matrix", headers=_alice_headers())
    assert resp.status_code == 200
    matrix = resp.json()["matrix"]
    for role, perms in matrix.items():
        for perm, val in perms.items():
            assert isinstance(val, bool), f"matrix[{role}][{perm}] is not bool: {val!r}"


# ---------------------------------------------------------------------------
# Phase-based audit snapshots (module)
# ---------------------------------------------------------------------------


def test_capture_phase_snapshot_returns_entry() -> None:
    clear_audit_log()
    entry = capture_phase_snapshot("doc-snap-1", "Review", actor="alice")
    assert entry.event == "phase_snapshot"
    assert entry.document_id == "doc-snap-1"
    assert entry.context.get("phase") == "Review"


def test_capture_phase_snapshot_stores_previous_phase() -> None:
    clear_audit_log()
    entry = capture_phase_snapshot(
        "doc-snap-2", "Final", actor="alice", previous_phase="Review"
    )
    assert entry.context.get("previous_phase") == "Review"


def test_get_phase_snapshots_returns_only_snapshots() -> None:
    clear_audit_log()
    log_audit_event("doc-snap-3", "document_uploaded", actor="alice")
    capture_phase_snapshot("doc-snap-3", "Draft", actor="alice")
    capture_phase_snapshot("doc-snap-3", "Review", actor="alice")
    snapshots = get_phase_snapshots("doc-snap-3")
    assert len(snapshots) == 2
    for s in snapshots:
        assert s.event == "phase_snapshot"


def test_get_phase_snapshots_empty_for_unknown_doc() -> None:
    clear_audit_log()
    assert get_phase_snapshots("nonexistent-doc-xyz") == []


def test_get_phase_snapshots_sorted_chronologically() -> None:
    clear_audit_log()
    capture_phase_snapshot("doc-order-chk", "Phase-A", actor="alice")
    capture_phase_snapshot("doc-order-chk", "Phase-B", actor="alice")
    snaps = get_phase_snapshots("doc-order-chk")
    times = [s.verified_at for s in snaps]
    assert times == sorted(times)


def test_capture_phase_snapshot_with_extra_context() -> None:
    clear_audit_log()
    entry = capture_phase_snapshot(
        "doc-ctx",
        "Review",
        actor="alice",
        context={"approved_by": "manager1", "ticket": "JIRA-42"},
    )
    assert entry.context.get("approved_by") == "manager1"
    assert entry.context.get("ticket") == "JIRA-42"


# ---------------------------------------------------------------------------
# Phase-based audit snapshots (API)
# ---------------------------------------------------------------------------


def test_api_create_phase_snapshot() -> None:
    clear_audit_log()
    doc = import_document("Snapshot API Test", b"body")
    client = TestClient(app)
    resp = client.post(
        f"/documents/{doc.id}/audit/snapshots",
        json={"phase": "Review"},
        headers=_alice_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["event"] == "phase_snapshot"
    assert data["context"]["phase"] == "Review"


def test_api_create_phase_snapshot_with_previous_phase() -> None:
    clear_audit_log()
    doc = import_document("Snapshot Prev Phase", b"body")
    client = TestClient(app)
    resp = client.post(
        f"/documents/{doc.id}/audit/snapshots",
        json={"phase": "Final", "previous_phase": "Review"},
        headers=_alice_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["context"].get("previous_phase") == "Review"


def test_api_list_phase_snapshots() -> None:
    clear_audit_log()
    doc = import_document("List Snapshots Test", b"body")
    capture_phase_snapshot(doc.id, "Draft", actor="alice")
    client = TestClient(app)
    resp = client.get(
        f"/documents/{doc.id}/audit/snapshots",
        headers=_alice_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(e["context"]["phase"] == "Draft" for e in data)


def test_api_create_snapshot_unknown_doc_returns_404() -> None:
    client = TestClient(app)
    resp = client.post(
        "/documents/no-such-doc-xyz/audit/snapshots",
        json={"phase": "Draft"},
        headers=_alice_headers(),
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Exportable audit package endpoint
# ---------------------------------------------------------------------------


def test_audit_export_returns_package() -> None:
    clear_audit_log()
    doc = import_document("Export doc", b"content")
    log_audit_event(doc.id, "document_uploaded", actor="alice")
    log_audit_event(doc.id, "document_reviewed", actor="alice")
    client = TestClient(app)
    resp = client.get(
        f"/documents/{doc.id}/audit/export",
        headers=_alice_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["document_id"] == doc.id
    assert "exported_at" in data
    assert "exported_by" in data
    # import_document itself may log events, so we check >= the 2 we added
    assert data["total_events"] >= 2
    assert "event_summary" in data
    assert isinstance(data["events"], list)
    assert len(data["events"]) >= 2


def test_audit_export_event_summary_counts() -> None:
    clear_audit_log()
    doc = import_document("Summary doc", b"content")
    log_audit_event(doc.id, "document_uploaded", actor="alice")
    log_audit_event(doc.id, "document_uploaded", actor="alice")
    log_audit_event(doc.id, "document_reviewed", actor="alice")
    client = TestClient(app)
    resp = client.get(f"/documents/{doc.id}/audit/export", headers=_alice_headers())
    assert resp.status_code == 200
    summary = resp.json()["event_summary"]
    # We explicitly log 2 document_uploaded + 1 document_reviewed; import_document
    # may add its own events, so check >= our explicitly added counts.
    assert summary.get("document_uploaded", 0) >= 2
    assert summary.get("document_reviewed", 0) >= 1


def test_audit_export_unknown_doc_returns_404() -> None:
    client = TestClient(app)
    resp = client.get("/documents/no-such-doc-export/audit/export", headers=_alice_headers())
    assert resp.status_code == 404


def test_audit_export_exported_by_is_caller() -> None:
    clear_audit_log()
    doc = import_document("Exporter doc", b"content")
    log_audit_event(doc.id, "document_uploaded", actor="alice")
    client = TestClient(app)
    resp = client.get(f"/documents/{doc.id}/audit/export", headers=_alice_headers())
    assert resp.status_code == 200
    assert resp.json()["exported_by"] == "alice"


# ---------------------------------------------------------------------------
# Executive summary dashboard
# ---------------------------------------------------------------------------


def test_executive_summary_returns_dict() -> None:
    result = executive_summary()
    assert isinstance(result, dict)
    assert "projects" in result
    assert "approvals" in result
    assert "documents" in result
    assert "phase_distribution" in result
    assert "generated_at" in result


def test_executive_summary_project_counts_non_negative() -> None:
    result = executive_summary()
    assert result["projects"]["total"] >= 0
    assert result["projects"]["active"] >= 0
    assert result["projects"]["with_overdue_approvals"] >= 0


def test_executive_summary_approval_rate_in_range() -> None:
    result = executive_summary()
    rate = result["approvals"]["approval_rate_pct"]
    assert 0.0 <= rate <= 100.0


def test_executive_summary_endpoint() -> None:
    client = TestClient(app)
    resp = client.get("/dashboard/executive-summary", headers=_alice_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert "projects" in data
    assert "approvals" in data
    assert "documents" in data


def test_executive_summary_phase_distribution_is_dict() -> None:
    result = executive_summary()
    assert isinstance(result["phase_distribution"], dict)


# ---------------------------------------------------------------------------
# Phase SLA module
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_sla_store() -> None:  # type: ignore[return]
    """Ensure a clean SLA store before each test."""
    clear_sla_store()
    yield
    clear_sla_store()


def test_set_and_get_phase_sla() -> None:
    cfg = set_phase_sla("Review", max_days=10, warning_days=2)
    assert cfg.phase == "Review"
    assert cfg.max_days == 10
    assert cfg.warning_days == 2
    retrieved = get_phase_sla("Review")
    assert retrieved is not None
    assert retrieved.max_days == 10


def test_get_phase_sla_missing_returns_none() -> None:
    assert get_phase_sla("NonExistentPhase") is None


def test_get_all_phase_slas_empty() -> None:
    assert get_all_phase_slas() == {}


def test_get_all_phase_slas_multiple() -> None:
    set_phase_sla("Draft", max_days=5, warning_days=1)
    set_phase_sla("Review", max_days=14, warning_days=3)
    slas = get_all_phase_slas()
    assert "Draft" in slas
    assert "Review" in slas


def test_delete_phase_sla_existing() -> None:
    set_phase_sla("Review", max_days=10, warning_days=2)
    existed = delete_phase_sla("Review")
    assert existed is True
    assert get_phase_sla("Review") is None


def test_delete_phase_sla_nonexistent() -> None:
    existed = delete_phase_sla("Phantom")
    assert existed is False


def test_phase_sla_warning_days_must_be_less_than_max() -> None:
    with pytest.raises(Exception):
        set_phase_sla("Review", max_days=5, warning_days=5)


def test_evaluate_phase_sla_ok() -> None:
    set_phase_sla("Review", max_days=10, warning_days=3)
    status = evaluate_phase_sla("Review", elapsed_days=2)
    assert status.status == "ok"
    assert status.elapsed_days == 2


def test_evaluate_phase_sla_warning() -> None:
    set_phase_sla("Review", max_days=10, warning_days=3)
    status = evaluate_phase_sla("Review", elapsed_days=8)
    assert status.status == "warning"


def test_evaluate_phase_sla_breached() -> None:
    set_phase_sla("Review", max_days=10, warning_days=3)
    status = evaluate_phase_sla("Review", elapsed_days=11)
    assert status.status == "breached"
    assert status.breach_in_days == 0


def test_evaluate_phase_sla_unknown_phase() -> None:
    status = evaluate_phase_sla("NoSLA", elapsed_days=5)
    assert status.status == "unknown"


def test_evaluate_phase_sla_exact_breach_boundary() -> None:
    set_phase_sla("Review", max_days=10, warning_days=3)
    status = evaluate_phase_sla("Review", elapsed_days=10)
    assert status.status == "breached"


def test_phase_sla_persists_to_disk(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import docreview360.phase_sla as sla_mod

    sla_file = tmp_path / "phase_sla_persist.json"
    monkeypatch.setattr(sla_mod, "_SLA_FILE", sla_file)
    monkeypatch.setattr(sla_mod, "_LOADED", False)
    monkeypatch.setattr(sla_mod, "_SLA_STORE", {})

    sla_mod.set_phase_sla("Persist", max_days=7, warning_days=1)
    assert sla_file.exists()

    # Reload from disk
    monkeypatch.setattr(sla_mod, "_LOADED", False)
    monkeypatch.setattr(sla_mod, "_SLA_STORE", {})
    retrieved = sla_mod.get_phase_sla("Persist")
    assert retrieved is not None
    assert retrieved.max_days == 7


# ---------------------------------------------------------------------------
# Phase SLA API endpoints
# ---------------------------------------------------------------------------


def test_api_get_all_slas_empty() -> None:
    client = TestClient(app)
    resp = client.get("/phases/sla", headers=_alice_headers())
    assert resp.status_code == 200
    assert resp.json()["slas"] == {}


def test_api_set_and_get_phase_sla() -> None:
    client = TestClient(app)
    resp = client.put(
        "/phases/Review/sla",
        json={"max_days": 14, "warning_days": 3},
        headers=_alice_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["max_days"] == 14
    assert data["warning_days"] == 3

    resp2 = client.get("/phases/Review/sla", headers=_alice_headers())
    assert resp2.status_code == 200
    assert resp2.json()["max_days"] == 14


def test_api_get_phase_sla_not_found() -> None:
    client = TestClient(app)
    resp = client.get("/phases/NonExistentSLA/sla", headers=_alice_headers())
    assert resp.status_code == 404


def test_api_delete_phase_sla() -> None:
    client = TestClient(app)
    client.put(
        "/phases/ToDelete/sla",
        json={"max_days": 5, "warning_days": 1},
        headers=_alice_headers(),
    )
    resp = client.delete("/phases/ToDelete/sla", headers=_alice_headers())
    assert resp.status_code == 204
    resp2 = client.get("/phases/ToDelete/sla", headers=_alice_headers())
    assert resp2.status_code == 404


def test_api_delete_phase_sla_not_found() -> None:
    client = TestClient(app)
    resp = client.delete("/phases/NoSLAPhase/sla", headers=_alice_headers())
    assert resp.status_code == 404


def test_api_evaluate_phase_sla_status() -> None:
    client = TestClient(app)
    client.put(
        "/phases/Eval/sla",
        json={"max_days": 10, "warning_days": 2},
        headers=_alice_headers(),
    )
    resp = client.get(
        "/phases/Eval/sla/status",
        params={"elapsed_days": 3},
        headers=_alice_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["elapsed_days"] == 3


def test_api_set_phase_sla_invalid_warning_days() -> None:
    client = TestClient(app)
    resp = client.put(
        "/phases/Bad/sla",
        json={"max_days": 5, "warning_days": 6},
        headers=_alice_headers(),
    )
    assert resp.status_code == 400


def test_api_sla_list_includes_all_set_phases() -> None:
    client = TestClient(app)
    client.put("/phases/Alpha/sla", json={"max_days": 5, "warning_days": 1}, headers=_alice_headers())
    client.put("/phases/Beta/sla", json={"max_days": 10, "warning_days": 2}, headers=_alice_headers())
    resp = client.get("/phases/sla", headers=_alice_headers())
    assert resp.status_code == 200
    slas = resp.json()["slas"]
    assert "Alpha" in slas
    assert "Beta" in slas

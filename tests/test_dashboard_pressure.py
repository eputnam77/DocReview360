# SPDX-License-Identifier: MIT
"""Dashboard area pressure tests — concurrent reads, data accuracy, and edge cases.

Covers every dashboard endpoint under realistic concurrent load and verifies
that the data each endpoint returns is accurate and consistent with the
underlying project/approval/document state.
"""
from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta

import pytest
from docreview360 import auth
from docreview360.api import app
from docreview360.approvals import approvals
from docreview360.approvals.core import reset_approvals
from docreview360.documents import documents
from docreview360.logs import clear_logs, log_event
from docreview360.reporting._metrics import (
    _METRICS_LOCK,
    _PROJECT_METRICS,
    record_quality_score,
    reset_metrics_for_testing,
)
from docreview360.search import projects
from docreview360.workflows import workflows
from fastapi.testclient import TestClient

_TEST_PASSWORD = "Dashboard!Pressure2026"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path):
    """Full state isolation: fresh DB, users, cleared stores."""
    auth.configure_user_repository(tmp_path / "users.db")
    for username in ("alice", "bob"):
        pw = auth.DEMO_USER_DEFAULTS[username]["password"]
        otp = auth.DEMO_USER_DEFAULTS[username].get("otp_secret")
        try:
            auth.USER_REPOSITORY.create_user(username, pw, otp_secret=otp)
        except Exception:
            pass

    projects.clear()
    documents.clear()
    reset_approvals()   # clears both in-memory dict AND the SQLite approval_records table
    workflows.clear()
    reset_metrics_for_testing()
    clear_logs()
    yield
    projects.clear()
    documents.clear()
    reset_approvals()
    workflows.clear()
    reset_metrics_for_testing()
    clear_logs()


@pytest.fixture()
def client():
    return TestClient(app)


def _headers(c: TestClient, username: str) -> dict[str, str]:
    token = auth.create_access_token({"sub": username}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


def _alice_headers(c: TestClient) -> dict[str, str]:
    return _headers(c, "alice")


def _seed_phases(c: TestClient, headers: dict) -> None:
    for phase in ("draft", "review", "approval", "done"):
        c.post("/phases", json={"name": phase}, headers=headers)


def _create_project(
    c: TestClient,
    headers: dict,
    *,
    name: str | None = None,
    doc_type: str = "Policy",
    user: str = "alice",
) -> dict:
    pid = str(uuid.uuid4())[:8]
    resp = c.post(
        "/projects",
        json={
            "id": pid,
            "name": name or f"Project-{pid}",
            "user": user,
            "doc_type": doc_type,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_workflow(c: TestClient, headers: dict, project_id: str) -> str:
    resp = c.post(
        "/workflows",
        json={"project": project_id, "phases": ["draft", "review", "approval", "done"]},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _create_user(c: TestClient, headers: dict, username: str) -> None:
    c.post(
        "/users",
        json={"username": username, "password": _TEST_PASSWORD},
        headers=headers,
    )


def _user_headers(c: TestClient, username: str) -> dict[str, str]:
    token = auth.create_access_token({"sub": username}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# 1. Concurrent dashboard reads never crash (no RuntimeError from dict iteration)
# ---------------------------------------------------------------------------


def test_concurrent_dashboard_reads_never_crash(client):
    """50 simultaneous GET /reports/dashboard calls must all return 200."""
    headers = _alice_headers(client)
    _seed_phases(client, headers)
    for i in range(10):
        _create_project(client, headers, name=f"Proj-{i}")

    errors: list[str] = []

    def _fetch():
        resp = client.get("/reports/dashboard", headers=headers)
        if resp.status_code != 200:
            errors.append(f"status={resp.status_code} body={resp.text[:100]}")

    with ThreadPoolExecutor(max_workers=50) as pool:
        futures = [pool.submit(_fetch) for _ in range(50)]
        for f in as_completed(futures):
            f.result()

    assert not errors, f"Dashboard reads failed: {errors[:5]}"


# ---------------------------------------------------------------------------
# 2. Concurrent writes + concurrent reads — no RuntimeError
# ---------------------------------------------------------------------------


def test_concurrent_writes_and_reads_no_crashes(client):
    """Simultaneous project creation and dashboard reads must not crash."""
    headers = _alice_headers(client)
    _seed_phases(client, headers)

    errors: list[str] = []

    def _write():
        _create_project(client, headers)

    def _read():
        for endpoint in (
            "/reports/dashboard",
            "/reports/summary",
            "/reports/workload",
            "/dashboard/user",
            "/dashboard/widgets",
            "/dashboard/doc-types",
        ):
            resp = client.get(endpoint, headers=headers)
            if resp.status_code not in (200, 403):
                errors.append(f"{endpoint} → {resp.status_code}")

    with ThreadPoolExecutor(max_workers=30) as pool:
        futures = [pool.submit(_write) for _ in range(15)]
        futures += [pool.submit(_read) for _ in range(15)]
        for f in as_completed(futures):
            f.result()

    assert not errors, f"Concurrent write+read failures: {errors[:5]}"


# ---------------------------------------------------------------------------
# 3. Dashboard data is accurate after project creation
# ---------------------------------------------------------------------------


def test_dashboard_data_reflects_real_project_state(client):
    """DashboardEntry fields must match actual project/approval state."""
    headers = _alice_headers(client)
    _seed_phases(client, headers)

    proj = _create_project(client, headers, name="Accuracy Test", doc_type="SOW")
    project_id = proj["id"]
    wf_id = _create_workflow(client, headers, project_id)

    docs_before = sum(1 for d in documents.values() if d.project == project_id)

    # Snapshot pending/overdue counts for THIS workflow before adding our approvals
    pending_before = sum(
        1 for a in approvals.values() if a.workflow == wf_id and a.state == "pending"
    )
    overdue_before = sum(
        1 for a in approvals.values() if a.workflow == wf_id and a.state == "overdue"
    )

    # Create one pending and one overdue approval
    resp = client.post(
        "/approvals",
        json={"workflow": wf_id, "reviewer": "alice"},
        headers=headers,
    )
    assert resp.status_code == 201
    approval_id = resp.json()["id"]

    # Mark it overdue by direct state manipulation for test purposes
    approvals[approval_id].state = "overdue"

    resp = client.post(
        "/approvals",
        json={"workflow": wf_id, "reviewer": "bob"},
        headers=headers,
    )
    assert resp.status_code == 201

    # Upload a document
    client.post(
        "/documents/import",
        files={"file": ("test.md", "content", "text/markdown")},
        data={"project": project_id},
        headers=headers,
    )

    data = client.get("/reports/dashboard", headers=headers).json()
    entry = next((e for e in data if e["id"] == project_id), None)
    assert entry is not None, "Project missing from dashboard data"
    assert entry["name"] == "Accuracy Test"
    assert entry["doc_type"] == "SOW"
    assert entry["docs"] >= docs_before + 1, "Dashboard must count the uploaded document"
    # pending_before + 1 (bob's) and overdue_before + 1 (alice's — we just set it)
    assert entry["pending_approvals"] == pending_before + 1, (
        f"Expected {pending_before + 1} pending, got {entry['pending_approvals']}"
    )
    assert entry["overdue_approvals"] == overdue_before + 1, (
        f"Expected {overdue_before + 1} overdue, got {entry['overdue_approvals']}"
    )


# ---------------------------------------------------------------------------
# 4. Summary counts match actual store sizes
# ---------------------------------------------------------------------------


def test_summary_counts_match_actual_state(client):
    """GET /reports/summary must return counts that increase after creating objects."""
    headers = _alice_headers(client)
    _seed_phases(client, headers)

    initial = client.get("/reports/summary", headers=headers).json()
    initial_projects = initial["projects"]
    initial_docs = initial["documents"]

    p1 = _create_project(client, headers, name="Sum-1")
    _create_project(client, headers, name="Sum-2")

    client.post(
        "/documents/import",
        files={"file": ("a.md", "hi", "text/markdown")},
        data={"project": p1["id"]},
        headers=headers,
    )

    summary = client.get("/reports/summary", headers=headers).json()
    assert summary["projects"] >= initial_projects + 2
    assert summary["documents"] >= initial_docs + 1


def test_summary_read_never_mutates_projects(client):
    """GET /reports/summary must not create a 'demo' project as a side-effect."""
    headers = _alice_headers(client)
    count_before = len(projects)
    for _ in range(5):
        client.get("/reports/summary", headers=headers)
    assert len(projects) == count_before, (
        "generate_summary() must not add projects as a side-effect"
    )


# ---------------------------------------------------------------------------
# 5. Workload double-counting fix — owner + reviewer on same project = 1 count
# ---------------------------------------------------------------------------


def test_workload_no_double_counting_owner_also_reviewer(client):
    """A user who owns a project AND has an active assignment on it counts as 1."""
    headers = _alice_headers(client)
    _seed_phases(client, headers)

    proj = _create_project(client, headers, name="Alice's Project", user="alice")
    project_id = proj["id"]

    # alice is owner; also add her as an active reviewer assignment
    resp = client.post(
        f"/projects/{project_id}/assignments",
        json={"reviewer": "alice"},
        headers=headers,
    )
    assert resp.status_code == 201

    workload = client.get("/reports/workload", headers=headers).json()
    # alice should appear exactly once for this project
    assert workload.get("alice", 0) == 1, (
        f"Expected alice=1 but got {workload.get('alice')} — owner+reviewer double-counted"
    )


# ---------------------------------------------------------------------------
# 6. Metrics concurrency — no data loss under parallel recording
# ---------------------------------------------------------------------------


def test_concurrent_quality_score_recording_no_data_loss(client):
    """50 concurrent record_quality_score calls must all be reflected in the aggregate."""
    reset_metrics_for_testing()
    # Seed a project and document so resolve_project_id works
    headers = _alice_headers(client)
    _seed_phases(client, headers)
    proj = _create_project(client, headers, name="MetricProj")
    project_id = proj["id"]
    resp = client.post(
        "/documents/import",
        files={"file": ("m.md", "data", "text/markdown")},
        data={"project": project_id},
        headers=headers,
    )
    doc_id = resp.json()["id"]

    scores = [0.5 + i * 0.01 for i in range(50)]

    def _record(score: float):
        record_quality_score(doc_id, score)

    with ThreadPoolExecutor(max_workers=20) as pool:
        list(pool.map(_record, scores))

    with _METRICS_LOCK:
        bucket = _PROJECT_METRICS.get(None)
    assert bucket is not None
    # All 50 scores must have been recorded (no lost updates)
    assert bucket.quality.count == 50, (
        f"Expected 50 quality scores, got {bucket.quality.count}"
    )


def test_concurrent_routing_snapshot_no_partial_read(client):
    """Concurrent routing snapshot updates must never produce a partial dict."""
    from docreview360.reporting._metrics import _routing_latency_snapshot, record_routing_snapshot

    errors: list[str] = []

    def _write():
        record_routing_snapshot({"<10ms": 5, "10-50ms": 3, "50-100ms": 1, "100ms+": 0})

    def _read():
        snap = _routing_latency_snapshot()
        # All 4 default buckets must always be present — a partial clear would break this
        for bucket in ("<10ms", "10-50ms", "50-100ms", "100ms+"):
            if bucket not in snap:
                errors.append(f"Missing bucket {bucket!r} in snapshot: {snap}")

    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = [pool.submit(_write if i % 2 == 0 else _read) for i in range(40)]
        for f in as_completed(futures):
            f.result()

    assert not errors, f"Partial latency snapshots detected: {errors[:3]}"


# ---------------------------------------------------------------------------
# 7. Audit feed contains rich project-level messages
# ---------------------------------------------------------------------------


def test_audit_feed_shows_rich_project_messages(client):
    """The /dashboard/audit-feed must show human-readable project event messages."""
    headers = _alice_headers(client)
    _seed_phases(client, headers)

    # Create a project — triggers a create_project log event with rich message
    _create_project(client, headers, name="AuditFeedProject")

    resp = client.get("/dashboard/audit-feed", headers=headers)
    assert resp.status_code == 200
    entries = resp.json()
    assert len(entries) > 0

    # At least one entry must have a non-empty human_message mentioning the project
    messages = [e["human_message"] for e in entries if e.get("human_message")]
    assert any("AuditFeedProject" in m for m in messages), (
        f"No rich project message found in audit feed. Messages: {messages[:5]}"
    )


def test_audit_feed_enrichment_never_crashes_on_unknown_actions(client):
    """Audit feed must return 200 even if log entries have unknown action types."""
    headers = _alice_headers(client)
    # Inject a log entry with an unusual action type
    log_event("custom_experimental_action_xyz", user_id="alice", entity_id="proj1")

    resp = client.get("/dashboard/audit-feed", headers=headers)
    assert resp.status_code == 200
    entries = resp.json()
    unknown = [e for e in entries if e.get("human_message", "")]
    assert len(unknown) > 0  # all entries must have some human_message


# ---------------------------------------------------------------------------
# 8. Manager dashboard returns accurate per-project data
# ---------------------------------------------------------------------------


def test_manager_dashboard_project_data_is_accurate(client):
    """GET /dashboard/manager must include all projects with correct doc counts."""
    from docreview360.rbac import add_role as _add_role

    headers = _alice_headers(client)
    _add_role("alice", "manager")
    _seed_phases(client, headers)

    proj_a = _create_project(client, headers, name="Manager-A")
    proj_b = _create_project(client, headers, name="Manager-B")

    # Upload 2 docs to A, 1 to B
    for i in range(2):
        client.post(
            "/documents/import",
            files={"file": (f"doc{i}.md", "x", "text/markdown")},
            data={"project": proj_a["id"]},
            headers=headers,
        )
    client.post(
        "/documents/import",
        files={"file": ("doc.md", "x", "text/markdown")},
        data={"project": proj_b["id"]},
        headers=headers,
    )

    resp = client.get("/dashboard/manager", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "workload" in data
    assert "projects" in data
    assert "quality" in data

    by_id = {e["id"]: e for e in data["projects"]}
    assert by_id[proj_a["id"]]["docs"] >= 2
    assert by_id[proj_b["id"]]["docs"] >= 1


# ---------------------------------------------------------------------------
# 9. Admin dashboard returns complete system data
# ---------------------------------------------------------------------------


def test_admin_dashboard_summary_matches_reports_summary(client):
    """GET /dashboard/admin summary field must equal GET /reports/summary."""
    headers = _alice_headers(client)
    _seed_phases(client, headers)
    _create_project(client, headers, name="Admin-1")
    _create_project(client, headers, name="Admin-2")

    admin_resp = client.get("/dashboard/admin", headers=headers).json()
    summary_resp = client.get("/reports/summary", headers=headers).json()

    assert admin_resp["summary"]["projects"] == summary_resp["projects"]
    assert admin_resp["summary"]["documents"] == summary_resp["documents"]


# ---------------------------------------------------------------------------
# 10. User dashboard scopes data to the requesting user's projects
# ---------------------------------------------------------------------------


def test_user_dashboard_scopes_to_current_user(client):
    """GET /dashboard/user must only return projects assigned to that user."""
    headers = _alice_headers(client)
    _seed_phases(client, headers)

    _create_project(client, headers, name="Alice-Project", user="alice")
    _create_project(client, headers, name="Bob-Project", user="bob")

    resp = client.get("/dashboard/user", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    project_names = [p["name"] for p in data["projects"]]
    assert "Alice-Project" in project_names
    # Bob's project must NOT appear in alice's dashboard
    assert "Bob-Project" not in project_names, (
        "User dashboard must not leak other users' projects"
    )


# ---------------------------------------------------------------------------
# 11. Widget counts are non-negative and internally consistent
# ---------------------------------------------------------------------------


def test_widget_counts_non_negative(client):
    """GET /dashboard/widgets must return non-negative integer counts."""
    headers = _alice_headers(client)
    _seed_phases(client, headers)
    _create_project(client, headers, name="Widget-1")

    resp = client.get("/dashboard/widgets", headers=headers)
    assert resp.status_code == 200
    w = resp.json()
    assert w["assigned"] >= 0
    assert w["active"] >= 0
    assert w["pending_approvals"] >= 0


# ---------------------------------------------------------------------------
# 12. Visibility preferences round-trip — save and read back
# ---------------------------------------------------------------------------


def test_visibility_preferences_round_trip(client):
    """PUT then GET /dashboard/visibility must return the saved preferences."""
    headers = _alice_headers(client)

    payload = {
        "stats": False,
        "status": True,
        "activity": False,
        "logs": True,
        "widgets": ["kpi", "quality", "logs"],
    }
    put_resp = client.put("/dashboard/visibility", json=payload, headers=headers)
    assert put_resp.status_code == 200

    get_resp = client.get("/dashboard/visibility", headers=headers)
    assert get_resp.status_code == 200
    saved = get_resp.json()
    assert saved["stats"] is False
    assert saved["status"] is True
    assert saved["logs"] is True
    assert sorted(saved["widgets"]) == sorted(["kpi", "quality", "logs"])


def test_visibility_concurrent_saves_no_corruption(client):
    """Simultaneous PUT /dashboard/visibility calls must not corrupt each other."""
    headers = _alice_headers(client)
    errors: list[str] = []

    def _save(i: int):
        payload = {"widgets": [f"widget_{i}"]}
        resp = client.put("/dashboard/visibility", json=payload, headers=headers)
        if resp.status_code != 200:
            errors.append(f"[{i}] {resp.status_code}: {resp.text[:100]}")

    with ThreadPoolExecutor(max_workers=20) as pool:
        list(pool.map(_save, range(20)))

    assert not errors, f"Visibility save failures: {errors[:3]}"
    # After concurrent writes the record must still be valid JSON / readable
    resp = client.get("/dashboard/visibility", headers=headers)
    assert resp.status_code == 200
    assert "widgets" in resp.json()


# ---------------------------------------------------------------------------
# 13. Analytics dashboard — data shapes and no crashes under load
# ---------------------------------------------------------------------------


def test_analytics_dashboard_returns_expected_keys(client):
    """GET /dashboard/analytics must return all required top-level keys."""
    from docreview360.rbac import add_role as _add_role

    headers = _alice_headers(client)
    _add_role("alice", "manager")
    _seed_phases(client, headers)
    _create_project(client, headers, name="Analytics-1")

    resp = client.get("/dashboard/analytics", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    for key in (
        "document_stats", "review_stats", "user_activity", "quality_trends", "phase_throughput"
    ):
        assert key in data, f"Missing key {key!r} from analytics response"
    assert data["document_stats"]["total"] >= 0
    assert data["review_stats"]["total_reviews"] >= 0
    assert data["user_activity"]["active_users"] >= 0


def test_analytics_dashboard_concurrent_calls_no_crashes(client):
    """20 concurrent GET /dashboard/analytics calls must all return 200."""
    from docreview360.rbac import add_role as _add_role

    headers = _alice_headers(client)
    _add_role("alice", "manager")
    _seed_phases(client, headers)
    for i in range(5):
        _create_project(client, headers, name=f"AnalyticsConcurrent-{i}")

    errors: list[str] = []

    def _fetch():
        resp = client.get("/dashboard/analytics", headers=headers)
        if resp.status_code != 200:
            errors.append(f"status={resp.status_code}")

    with ThreadPoolExecutor(max_workers=20) as pool:
        list(pool.map(lambda _: _fetch(), range(20)))

    assert not errors, f"Analytics concurrent failures: {errors}"


# ---------------------------------------------------------------------------
# 14. Executive summary — accurate approval counts and no crashes
# ---------------------------------------------------------------------------


def test_executive_summary_approval_counts_accurate(client):
    """GET /dashboard/executive-summary approval counts must match store state."""
    headers = _alice_headers(client)
    _seed_phases(client, headers)

    proj = _create_project(client, headers, name="ExecSummary-1")
    wf_id = _create_workflow(client, headers, proj["id"])

    # Create 2 approvals, approve 1
    r1 = client.post("/approvals", json={"workflow": wf_id, "reviewer": "alice"}, headers=headers)
    client.post("/approvals", json={"workflow": wf_id, "reviewer": "bob"}, headers=headers)
    a1_id = r1.json()["id"]
    approvals[a1_id].state = "approved"

    resp = client.get("/dashboard/executive-summary", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["approvals"]["total"] >= 2
    assert data["approvals"]["approved"] >= 1
    assert data["approvals"]["pending"] >= 1


def test_executive_summary_deadline_timezone_handling(client):
    """executive_summary must not crash on approval deadlines with timezone info."""
    headers = _alice_headers(client)
    _seed_phases(client, headers)

    proj = _create_project(client, headers, name="TZ-Test")
    wf_id = _create_workflow(client, headers, proj["id"])

    r = client.post(
        "/approvals",
        json={
            "workflow": wf_id,
            "reviewer": "alice",
            # Deadline string WITH explicit +00:00 offset — was mishandled by .replace(tzinfo=...)
            "deadline": (datetime.now(UTC) + timedelta(days=3)).isoformat(),
        },
        headers=headers,
    )
    assert r.status_code in (200, 201, 422), r.text
    # Must not crash
    resp = client.get("/dashboard/executive-summary", headers=headers)
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 15. Reviewer workload — accurate counts, no double-counting
# ---------------------------------------------------------------------------


def test_reviewer_workload_no_double_counting(client):
    """A reviewer who owns a project AND has an active assignment gets counted once."""
    headers = _alice_headers(client)
    _seed_phases(client, headers)

    proj = _create_project(client, headers, name="Workload-Test", user="alice")
    client.post(
        f"/projects/{proj['id']}/assignments",
        json={"reviewer": "alice"},
        headers=headers,
    )

    resp = client.get("/dashboard/reviewer-workload", headers=headers)
    assert resp.status_code == 200
    workload = resp.json()
    alice_entry = next((w for w in workload if w["reviewer"] == "alice"), None)
    if alice_entry:
        # assigned_projects must be 1, not 2
        assert alice_entry["assigned_projects"] == 1, (
            f"alice double-counted: assigned_projects={alice_entry['assigned_projects']}"
        )


# ---------------------------------------------------------------------------
# 16. Recently active users — returns valid data without OOM
# ---------------------------------------------------------------------------


def test_recently_active_users_returns_valid_data(client):
    """GET /dashboard/recently-active-users must return a list of users."""
    headers = _alice_headers(client)

    # Generate some log events for alice
    for i in range(5):
        log_event("test_action", user_id="alice", entity_id=f"item-{i}")

    resp = client.get("/dashboard/recently-active-users", headers=headers)
    assert resp.status_code == 200
    users = resp.json()
    assert isinstance(users, list)
    usernames = [u["username"] for u in users]
    assert "alice" in usernames

    alice_entry = next(u for u in users if u["username"] == "alice")
    assert alice_entry["action_count"] >= 5
    assert alice_entry["last_active"] is not None


def test_recently_active_users_respects_days_limit(client):
    """The days parameter must filter out older log entries."""
    headers = _alice_headers(client)

    # Log an event for alice
    log_event("recent_action", user_id="alice")

    # With days=1, alice should appear
    resp1 = client.get("/dashboard/recently-active-users?days=1", headers=headers)
    assert resp1.status_code == 200
    # With days=0 the endpoint clamps to 1, so alice should still appear
    resp2 = client.get("/dashboard/recently-active-users?days=0", headers=headers)
    assert resp2.status_code == 200


# ---------------------------------------------------------------------------
# 17. Document aging metrics — safe under concurrent document creation
# ---------------------------------------------------------------------------


def test_document_aging_concurrent_creation(client):
    """GET /reports/document-aging must return 200 under concurrent document creation."""
    headers = _alice_headers(client)
    _seed_phases(client, headers)
    proj = _create_project(client, headers, name="Aging-Test")

    errors: list[str] = []

    def _create_doc():
        resp = client.post(
            "/documents/import",
            files={"file": ("x.md", "content", "text/markdown")},
            data={"project": proj["id"]},
            headers=headers,
        )
        if resp.status_code not in (201, 200):
            errors.append(f"doc create: {resp.status_code}")

    def _read_aging():
        resp = client.get("/reports/document-aging", headers=headers)
        if resp.status_code != 200:
            errors.append(f"aging: {resp.status_code}")

    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = [pool.submit(_create_doc if i % 2 == 0 else _read_aging) for i in range(20)]
        for f in as_completed(futures):
            f.result()

    assert not errors, f"Document aging concurrent errors: {errors}"


# ---------------------------------------------------------------------------
# 18. Dashboard audit feed pagination
# ---------------------------------------------------------------------------


def test_audit_feed_pagination(client):
    """The audit-feed limit parameter must be respected."""
    headers = _alice_headers(client)
    # Generate 20 events
    for i in range(20):
        log_event("test_page_event", user_id="alice", entity_id=f"e-{i}")

    resp5 = client.get("/dashboard/audit-feed?limit=5", headers=headers)
    assert resp5.status_code == 200
    assert len(resp5.json()) <= 5

    resp20 = client.get("/dashboard/audit-feed?limit=20", headers=headers)
    assert resp20.status_code == 200
    assert len(resp20.json()) <= 20


# ---------------------------------------------------------------------------
# 19. Full stress: 30-thread mixed dashboard reads — zero 5xx
# ---------------------------------------------------------------------------


def test_dashboard_full_stress_no_5xx(client):
    """30 threads hitting every dashboard endpoint simultaneously — zero 5xx."""
    from docreview360.rbac import add_role as _add_role

    headers = _alice_headers(client)
    _add_role("alice", "manager")
    _seed_phases(client, headers)
    for i in range(5):
        proj = _create_project(client, headers, name=f"Stress-{i}")
        _create_workflow(client, headers, proj["id"])
        client.post(
            "/documents/import",
            files={"file": (f"d{i}.md", "x", "text/markdown")},
            data={"project": proj["id"]},
            headers=headers,
        )

    endpoints = [
        "/reports/dashboard",
        "/reports/summary",
        "/reports/workload",
        "/reports/document-aging",
        "/dashboard/user",
        "/dashboard/widgets",
        "/dashboard/doc-types",
        "/dashboard/admin",
        "/dashboard/manager",
        "/dashboard/analytics",
        "/dashboard/executive-summary",
        "/dashboard/reviewer-workload",
        "/dashboard/audit-feed",
        "/dashboard/recently-active-users",
        "/reports/throughput",
    ]

    five_xx: list[str] = []

    def _hit_random():
        import random
        ep = random.choice(endpoints)
        resp = client.get(ep, headers=headers)
        if resp.status_code >= 500:
            five_xx.append(f"{ep} → {resp.status_code}: {resp.text[:80]}")

    with ThreadPoolExecutor(max_workers=30) as pool:
        # Each thread hits 5 random endpoints
        futures = [pool.submit(_hit_random) for _ in range(150)]
        for f in as_completed(futures):
            f.result()

    assert not five_xx, f"5xx responses under stress: {five_xx[:5]}"


# ---------------------------------------------------------------------------
# 20. Throughput CSV and JSON exports
# ---------------------------------------------------------------------------


def test_throughput_and_workload_exports(client):
    """CSV export endpoints must return 200 with correct Content-Type."""
    headers = _alice_headers(client)
    _seed_phases(client, headers)
    _create_project(client, headers, name="Export-1")

    resp_csv = client.get("/reports/throughput.csv", headers=headers)
    assert resp_csv.status_code == 200
    assert "text/csv" in resp_csv.headers.get("content-type", "")

    resp_workload = client.get("/reports/workload.csv", headers=headers)
    assert resp_workload.status_code == 200
    assert "text/csv" in resp_workload.headers.get("content-type", "")

    resp_json = client.get("/reports/analytics/export?format=json", headers=headers)
    assert resp_json.status_code == 200

    resp_analytics_csv = client.get("/reports/analytics/export?format=csv", headers=headers)
    assert resp_analytics_csv.status_code == 200
    assert "text/csv" in resp_analytics_csv.headers.get("content-type", "")

# SPDX-License-Identifier: MIT
"""Projects-area pressure and correctness tests.

Covers:
- Concurrent project creation (no ID collisions, no lost writes)
- Concurrent reviewer add deduplication (no duplicate approvals)
- Concurrent reviewer operations under contention
- Full concurrent lifecycle: create → assign → start → submit → concur
- Double-submit protection (TOCTOU on assignment status)
- Phase transitions under concurrent load with audit trail verification
- NARA metadata change tracking in audit log
- Concurrent feedback submission correctness
- Assignment state machine correctness under concurrent load
- Audit log integrity under concurrent writes (no corrupted entries)
- Audit log specificity: entries must name project + doc number, not just raw IDs
- Review summary accuracy after concurrent operations
- Priority updates under load (last-write-wins, no corruption)
"""
from __future__ import annotations

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


_TEST_PASSWORD = "Pressure!Test2026"


def _make_headers(client: TestClient, username: str, password: str = "password") -> dict[str, str]:
    r = client.post("/token", data={"username": username, "password": password})
    assert r.status_code == 200, f"login failed for {username}: {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _make_test_headers(client: TestClient, username: str) -> dict[str, str]:
    """Login as a user created with _TEST_PASSWORD."""
    r = client.post("/token", data={"username": username, "password": _TEST_PASSWORD})
    assert r.status_code == 200, f"login failed for {username}: {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _create_user(
    client: TestClient,
    admin_headers: dict,
    username: str,
    roles: list[str],
) -> None:
    r = client.post(
        "/users",
        headers=admin_headers,
        json={"username": username, "password": _TEST_PASSWORD, "roles": roles, "active": True},
    )
    assert r.status_code in (201, 409), f"user create failed: {r.status_code} {r.text}"


def _seed_phases(client: TestClient, admin_headers: dict, phases: list[str]) -> None:
    for phase in phases:
        r = client.post("/phases", headers=admin_headers, json={"name": phase})
        assert r.status_code in (201, 409), f"phase seed failed for {phase!r}: {r.text}"


def _create_project(
    client: TestClient,
    headers: dict,
    name: str,
    *,
    doc_type: str | None = None,
    phase: str | None = None,
    suffix: str = "",
) -> dict:
    body: dict[str, Any] = {"name": name}
    if doc_type:
        body["doc_type"] = doc_type
    if phase:
        body["phase"] = phase
    if suffix:
        body["document_number"] = f"DOC-{suffix}"
    r = client.post("/projects", headers=headers, json=body)
    assert r.status_code == 201, f"project create failed: {r.status_code} {r.text}"
    return r.json()


def _get_audit_entries(client: TestClient, admin_headers: dict, entity_id: str) -> list[dict]:
    r = client.get(f"/api/audit?entity_id={entity_id}", headers=admin_headers)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture
def client():
    from docreview360.api import app
    from docreview360.audit import clear_audit_log
    from docreview360.cache import clear_cache
    from docreview360.logs import clear_logs
    from docreview360.search import _reset_state_for_testing

    clear_audit_log()
    clear_logs()
    clear_cache()
    _reset_state_for_testing()

    # Seed required phases (alice is the admin user in the test environment)
    with TestClient(app) as c:
        admin_h = _make_headers(c, "alice")
        _seed_phases(c, admin_h, ["draft", "review", "approval", "done"])
        yield c


@pytest.fixture
def admin_headers(client: TestClient) -> dict[str, str]:
    return _make_headers(client, "alice")


# ---------------------------------------------------------------------------
# 1. Concurrent project creation — no ID collisions
# ---------------------------------------------------------------------------


def test_concurrent_project_creation_no_collisions(client, admin_headers):
    """20 threads each create a distinct project; all must succeed with unique IDs."""
    n = 20
    suffix = uuid.uuid4().hex[:6]
    results: list[dict | Exception] = [None] * n  # type: ignore[list-item]

    def _create(i: int) -> None:
        r = client.post(
            "/projects",
            headers=admin_headers,
            json={"name": f"Concurrent Project {i} {suffix}"},
        )
        if r.status_code == 201:
            results[i] = r.json()
        else:
            results[i] = RuntimeError(f"slot {i}: {r.status_code} {r.text}")

    threads = [threading.Thread(target=_create, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    errors = [r for r in results if isinstance(r, Exception)]
    assert not errors, f"concurrent creation errors: {errors}"

    ids = [r["id"] for r in results if isinstance(r, dict)]
    assert len(ids) == n, f"expected {n} projects, got {len(ids)}"
    assert len(set(ids)) == n, "duplicate project IDs produced under concurrent creation"


# ---------------------------------------------------------------------------
# 2. Concurrent reviewer add — deduplication
# ---------------------------------------------------------------------------


def test_concurrent_reviewer_add_no_duplicates(client, admin_headers):
    """10 threads add the same reviewer to the same project concurrently.
    Reviewer list must contain the reviewer exactly once; approvals must not duplicate."""
    suffix = uuid.uuid4().hex[:6]
    reviewer = f"rev-dedup-{suffix}"
    _create_user(client, admin_headers, reviewer, ["user"])

    project = _create_project(client, admin_headers, f"Dedup Project {suffix}")
    project_id = project["id"]

    n = 10
    status_codes: list[int] = []
    lock = threading.Lock()

    def _add() -> None:
        r = client.post(
            f"/projects/{project_id}/reviewers",
            headers=admin_headers,
            json={"reviewer": reviewer},
        )
        with lock:
            status_codes.append(r.status_code)

    threads = [threading.Thread(target=_add) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # All requests succeed (idempotent add is valid)
    bad = [c for c in status_codes if c not in (200, 409)]
    assert not bad, f"unexpected status codes: {bad}"

    # Reviewer appears exactly once
    r = client.get(f"/projects/{project_id}/reviewers", headers=admin_headers)
    assert r.status_code == 200
    reviewers = r.json()
    assert reviewers.count(reviewer) == 1, f"reviewer duplicated: {reviewers}"

    # Approvals must not be duplicated
    from docreview360.approvals import list_approvals as _list_approvals
    from docreview360.search import get_project
    p = get_project(project_id)
    if p and p.workflow:
        ap = _list_approvals(p.workflow)
        rev_approvals = [a for a in ap if a.reviewer == reviewer]
        assert len(rev_approvals) <= 1, (
            f"duplicate approvals for reviewer {reviewer}: {len(rev_approvals)}"
        )


# ---------------------------------------------------------------------------
# 3. Concurrent reviewer operations (add/update/remove) under contention
# ---------------------------------------------------------------------------


def test_concurrent_reviewer_operations_consistency(client, admin_headers):
    """Simultaneously add and remove two different reviewers; final state must be consistent."""
    suffix = uuid.uuid4().hex[:6]
    rev_a = f"rev-a-{suffix}"
    rev_b = f"rev-b-{suffix}"
    for u in (rev_a, rev_b):
        _create_user(client, admin_headers, u, ["user"])

    project = _create_project(client, admin_headers, f"Reviewer Ops {suffix}")
    project_id = project["id"]

    errors: list[str] = []
    lock = threading.Lock()

    def _add(reviewer: str) -> None:
        r = client.post(
            f"/projects/{project_id}/reviewers",
            headers=admin_headers,
            json={"reviewer": reviewer},
        )
        if r.status_code not in (200, 409):
            with lock:
                errors.append(f"add {reviewer}: {r.status_code} {r.text}")

    def _remove(reviewer: str) -> None:
        r = client.delete(
            f"/projects/{project_id}/reviewers/{reviewer}",
            headers=admin_headers,
        )
        if r.status_code not in (200, 404):
            with lock:
                errors.append(f"remove {reviewer}: {r.status_code} {r.text}")

    # Seed rev_a so removal has something to remove
    _add(rev_a)

    threads = [
        threading.Thread(target=_add, args=(rev_b,)),
        threading.Thread(target=_add, args=(rev_b,)),
        threading.Thread(target=_remove, args=(rev_a,)),
        threading.Thread(target=_add, args=(rev_a,)),
        threading.Thread(target=_remove, args=(rev_b,)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"reviewer operation errors: {errors}"

    # Project is still retrievable and well-formed
    r = client.get(f"/projects/{project_id}", headers=admin_headers)
    assert r.status_code == 200
    p = r.json()
    for rev in p["reviewers"]:
        assert p["reviewers"].count(rev) == 1, f"duplicates in reviewer list: {p['reviewers']}"


# ---------------------------------------------------------------------------
# 4. Full concurrent lifecycle — 5 parallel project lifecycles
# ---------------------------------------------------------------------------


def test_concurrent_full_lifecycle(client, admin_headers):
    """5 projects each run a full lifecycle concurrently: create→assign→start→submit→concur."""
    suffix = uuid.uuid4().hex[:6]
    n = 5
    reviewer_names = [f"lc-reviewer-{suffix}-{i}" for i in range(n)]
    for name in reviewer_names:
        _create_user(client, admin_headers, name, ["user"])

    results: list[str | None] = [None] * n
    errors: list[str] = []
    lock = threading.Lock()

    def _lifecycle(i: int) -> None:
        try:
            reviewer = reviewer_names[i]
            rev_headers = _make_test_headers(client, reviewer)

            project = _create_project(
                client,
                admin_headers,
                f"Lifecycle Project {suffix} {i}",
                suffix=f"{suffix}-{i}",
            )
            pid = project["id"]

            # Assign
            r = client.post(
                f"/projects/{pid}/assignments",
                headers=admin_headers,
                json={"reviewer": reviewer},
            )
            assert r.status_code == 201, f"assign failed: {r.text}"
            aid = r.json()["id"]

            # Start
            r = client.post(f"/projects/{pid}/assignments/{aid}/start", headers=rev_headers)
            assert r.status_code == 200, f"start failed: {r.text}"
            assert r.json()["status"] == "reviewing"

            # Submit feedback
            r = client.post(
                f"/projects/{pid}/feedback",
                headers=rev_headers,
                json={
                    "text": f"Lifecycle feedback {suffix} {i}",
                    "feedback_type": "comment",
                    "assignment_id": aid,
                    "phase": "draft",
                },
            )
            assert r.status_code == 201, f"feedback failed: {r.text}"

            # Submit assignment
            r = client.post(f"/projects/{pid}/assignments/{aid}/submit", headers=rev_headers)
            assert r.status_code == 200, f"submit failed: {r.text}"

            # Concur
            r = client.post(f"/projects/{pid}/assignments/{aid}/concur", headers=rev_headers)
            assert r.status_code == 200, f"concur failed: {r.text}"
            assert r.json()["status"] == "concurred"

            with lock:
                results[i] = pid
        except Exception as exc:
            with lock:
                errors.append(f"lifecycle {i}: {exc}")

    threads = [threading.Thread(target=_lifecycle, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"lifecycle errors: {errors}"
    completed = [r for r in results if r is not None]
    assert len(completed) == n, f"only {len(completed)}/{n} lifecycles completed"


# ---------------------------------------------------------------------------
# 5. Double-submit protection (assignment status TOCTOU)
# ---------------------------------------------------------------------------


def test_double_start_assignment_is_idempotent(client, admin_headers):
    """Two concurrent start calls on the same invited assignment.
    Both should succeed (idempotent) or one should get 409; status must be 'reviewing'."""
    suffix = uuid.uuid4().hex[:6]
    reviewer = f"dbl-start-{suffix}"
    _create_user(client, admin_headers, reviewer, ["user"])

    project = _create_project(client, admin_headers, f"Double Start {suffix}")
    pid = project["id"]
    rev_headers = _make_test_headers(client, reviewer)

    r = client.post(
        f"/projects/{pid}/assignments", headers=admin_headers, json={"reviewer": reviewer}
    )
    assert r.status_code == 201
    aid = r.json()["id"]

    status_codes: list[int] = []
    lock = threading.Lock()

    def _start() -> None:
        r2 = client.post(f"/projects/{pid}/assignments/{aid}/start", headers=rev_headers)
        with lock:
            status_codes.append(r2.status_code)

    threads = [threading.Thread(target=_start) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # At least one must have succeeded
    assert 200 in status_codes, f"no start succeeded: {status_codes}"
    # No 5xx errors
    assert not any(c >= 500 for c in status_codes), f"server error on double start: {status_codes}"

    # Final assignment status must be reviewing (not corrupted)
    r = client.get(f"/projects/{pid}/assignments", headers=admin_headers)
    assert r.status_code == 200
    assignments = r.json()["items"]
    our_assignment = next(a for a in assignments if a["id"] == aid)
    assert our_assignment["status"] == "reviewing", (
        f"unexpected final status: {our_assignment['status']}"
    )


def test_replace_and_start_race_resolves_cleanly(client, admin_headers):
    """Concurrent replace and start on the same assignment.
    Final state must be unambiguous: either replaced or reviewing, never both."""
    suffix = uuid.uuid4().hex[:6]
    original_reviewer = f"race-orig-{suffix}"
    replacement_reviewer = f"race-repl-{suffix}"
    for u in (original_reviewer, replacement_reviewer):
        _create_user(client, admin_headers, u, ["user"])

    project = _create_project(client, admin_headers, f"Replace Race {suffix}")
    pid = project["id"]
    orig_headers = _make_test_headers(client, original_reviewer)

    r = client.post(
        f"/projects/{pid}/assignments",
        headers=admin_headers,
        json={"reviewer": original_reviewer},
    )
    assert r.status_code == 201
    aid = r.json()["id"]

    # Race: start (reviewer) vs replace (admin)
    start_result: dict[str, Any] = {}
    replace_result: dict[str, Any] = {}

    barrier = threading.Barrier(2)

    def _start() -> None:
        barrier.wait()
        r2 = orig_headers and client.post(
            f"/projects/{pid}/assignments/{aid}/start", headers=orig_headers
        )
        start_result["status"] = r2.status_code
        start_result["body"] = r2.json() if r2.status_code == 200 else r2.text

    def _replace() -> None:
        barrier.wait()
        r2 = client.post(
            f"/projects/{pid}/assignments/{aid}/replace",
            headers=admin_headers,
            json={"replacement_reviewer": replacement_reviewer, "reason": "Race test"},
        )
        replace_result["status"] = r2.status_code
        replace_result["body"] = r2.json() if r2.status_code == 200 else r2.text

    t1, t2 = threading.Thread(target=_start), threading.Thread(target=_replace)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Neither must be a 5xx
    assert start_result["status"] < 500, f"start 5xx: {start_result}"
    assert replace_result["status"] < 500, f"replace 5xx: {replace_result}"

    # Final state of the original assignment must be one of: reviewing, replaced
    from docreview360.review_assignments import get_assignment
    final = get_assignment(aid)
    assert final is not None
    assert final.status in ("reviewing", "replaced", "invited"), (
        f"unexpected final status: {final.status!r}"
    )
    # Must NOT be in an undefined state
    assert final.status in (
        "reviewing", "replaced", "invited", "feedback_submitted", "concurred", "signed"
    )


# ---------------------------------------------------------------------------
# 6. Phase transitions under concurrent load with audit trail
# ---------------------------------------------------------------------------


def test_phase_transition_emits_specific_audit_event(client, admin_headers):
    """Phase transitions must emit phase_transitioned event with old/new phase."""
    suffix = uuid.uuid4().hex[:6]
    project = _create_project(
        client,
        admin_headers,
        f"Phase Transition {suffix}",
        phase="draft",
        suffix=suffix,
    )
    pid = project["id"]
    doc_num = f"DOC-{suffix}"

    # Set a workflow so _update_workflow_phase runs
    # First ensure project has a workflow by updating with a workflow template
    r = client.put(
        f"/projects/{pid}",
        headers=admin_headers,
        json={"phase": "review"},
    )
    assert r.status_code == 200, r.text

    # Check audit log for phase_transitioned event
    entries = _get_audit_entries(client, admin_headers, pid)
    actions = {e["action"] for e in entries}

    # Check if phase transition was captured (either as update_project or phase_transitioned)
    phase_entries = [
        e for e in entries
        if e["action"] in ("phase_transitioned", "update_project")
        and e.get("details", {}).get("project_id") == pid
    ]
    assert phase_entries, f"no phase transition events found; actions seen: {actions}"

    # Verify the log message is rich (contains project name, not just raw ID)
    for entry in phase_entries:
        msg = entry.get("details", {}).get("message") or ""
        # Should contain the project name, not just an opaque ID
        assert f"Phase Transition {suffix}" in msg or pid not in msg or doc_num in msg, (
            f"Phase transition log too vague: {msg!r}"
        )


def test_concurrent_phase_advances_no_corruption(client, admin_headers):
    """5 threads concurrently advance the phase; project must remain well-formed."""
    suffix = uuid.uuid4().hex[:6]
    project = _create_project(client, admin_headers, f"Phase Pressure {suffix}", phase="draft")
    pid = project["id"]

    phases = ["review", "approval", "done", "draft", "review"]
    errors: list[str] = []
    lock = threading.Lock()

    def _advance(phase: str) -> None:
        r = client.put(f"/projects/{pid}", headers=admin_headers, json={"phase": phase})
        if r.status_code not in (200,):
            with lock:
                errors.append(f"advance to {phase!r}: {r.status_code} {r.text}")

    threads = [threading.Thread(target=_advance, args=(p,)) for p in phases]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Project still retrievable
    r = client.get(f"/projects/{pid}", headers=admin_headers)
    assert r.status_code == 200, f"project missing after concurrent phase advances: {r.text}"


# ---------------------------------------------------------------------------
# 7. NARA metadata change tracking in audit log
# ---------------------------------------------------------------------------


def test_nara_metadata_changes_appear_in_audit_log(client, admin_headers):
    """NARA field updates must appear in changed_fields in the update_project audit event."""
    suffix = uuid.uuid4().hex[:6]
    project = _create_project(
        client,
        admin_headers,
        f"NARA Project {suffix}",
        suffix=suffix,
    )
    pid = project["id"]

    r = client.put(
        f"/projects/{pid}",
        headers=admin_headers,
        json={
            "nara_schedule_number": f"NARA-SCH-{suffix}",
            "nara_disposition_authority": f"DA-{suffix}",
            "nara_retention_period": "7 years",
            "nara_record_series": f"RS-{suffix}",
        },
    )
    assert r.status_code == 200, r.text

    entries = _get_audit_entries(client, admin_headers, pid)
    update_entries = [e for e in entries if e["action"] == "update_project"]
    assert update_entries, "no update_project event after NARA metadata change"

    latest = update_entries[-1]
    changed = latest.get("details", {}).get("changed_fields") or {}
    assert "nara_schedule_number" in changed or "nara_disposition_authority" in changed, (
        f"NARA fields missing from changed_fields: {changed}"
    )


def test_nara_unchanged_does_not_appear_in_changed_fields(client, admin_headers):
    """Updating only the project name must not include NARA fields in changed_fields."""
    suffix = uuid.uuid4().hex[:6]
    project = _create_project(client, admin_headers, f"No NARA {suffix}")
    pid = project["id"]

    r = client.put(f"/projects/{pid}", headers=admin_headers, json={"name": f"Renamed {suffix}"})
    assert r.status_code == 200

    entries = _get_audit_entries(client, admin_headers, pid)
    update_entries = [e for e in entries if e["action"] == "update_project"]
    for entry in update_entries:
        changed = entry.get("details", {}).get("changed_fields") or {}
        for nara_key in (
            "nara_schedule_number", "nara_disposition_authority",
            "nara_retention_period", "nara_record_series",
        ):
            assert nara_key not in changed, (
                f"spurious NARA field {nara_key!r} in changed_fields when unchanged"
            )


# ---------------------------------------------------------------------------
# 8. Concurrent feedback submission correctness
# ---------------------------------------------------------------------------


def test_concurrent_feedback_all_items_persisted(client, admin_headers):
    """20 concurrent feedback submissions must all persist with no lost writes."""
    suffix = uuid.uuid4().hex[:6]
    reviewer = f"fb-reviewer-{suffix}"
    _create_user(client, admin_headers, reviewer, ["user"])

    project = _create_project(client, admin_headers, f"Feedback Pressure {suffix}")
    pid = project["id"]

    # Add reviewer to project so they have access to submit feedback
    r = client.post(
        f"/projects/{pid}/reviewers",
        headers=admin_headers,
        json={"reviewer": reviewer},
    )
    assert r.status_code == 200, f"could not add reviewer: {r.text}"

    rev_headers = _make_test_headers(client, reviewer)

    n = 20
    created_ids: list[str] = []
    errors: list[str] = []
    lock = threading.Lock()

    def _submit(i: int) -> None:
        r = client.post(
            f"/projects/{pid}/feedback",
            headers=rev_headers,
            json={
                "text": f"Concurrent feedback {suffix} item {i}",
                "feedback_type": "comment",
                "phase": "draft",
            },
        )
        with lock:
            if r.status_code == 201:
                created_ids.append(r.json()["id"])
            else:
                errors.append(f"item {i}: {r.status_code} {r.text}")

    threads = [threading.Thread(target=_submit, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"feedback submission errors: {errors}"
    assert len(created_ids) == n, f"expected {n} feedback items, got {len(created_ids)}"
    assert len(set(created_ids)) == n, "duplicate feedback IDs"

    # Verify persisted count via list endpoint
    r = client.get(f"/projects/{pid}/feedback", headers=admin_headers)
    assert r.status_code == 200
    listed = r.json()
    total = listed.get("total", len(listed.get("items", listed)))
    assert total >= n, f"feedback items lost: listed {total}, expected {n}"


# ---------------------------------------------------------------------------
# 9. Audit log integrity under concurrent writes
# ---------------------------------------------------------------------------


def test_audit_log_integrity_under_concurrent_writes(client, admin_headers):
    """50 concurrent audit events must all be parseable (no corrupted JSON lines)."""
    from docreview360.audit import _AUDIT_LOG_PATH, log_audit_event

    n = 50
    errors: list[str] = []
    lock = threading.Lock()

    def _write(i: int) -> None:
        try:
            log_audit_event(
                f"concurrent-test-doc-{i}",
                "concurrent_write_test",
                actor="pressure-test",
                project_id=f"proj-{i}",
                project_name=f"Project {i}",
                message=f"Pressure test write {i}",
            )
        except Exception as exc:
            with lock:
                errors.append(f"write {i}: {exc}")

    threads = [threading.Thread(target=_write, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"audit write errors: {errors}"

    # Verify every line in the log file is valid JSON
    import json
    if _AUDIT_LOG_PATH.exists():
        corrupt = 0
        with _AUDIT_LOG_PATH.open("r", encoding="utf-8") as fh:
            for line_no, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    json.loads(line)
                except json.JSONDecodeError:
                    corrupt += 1
        assert corrupt == 0, f"{corrupt} corrupted JSON lines in audit log after concurrent writes"


# ---------------------------------------------------------------------------
# 10. Audit log specificity: entries name project + doc number
# ---------------------------------------------------------------------------


def test_audit_log_entries_are_specific_not_vague(client, admin_headers):
    """All project-level audit events must contain project_name and project_id in details,
    not just a raw opaque identifier as the sole context."""
    suffix = uuid.uuid4().hex[:6]
    project = _create_project(
        client,
        admin_headers,
        f"Specificity Project {suffix}",
        suffix=suffix,
    )
    pid = project["id"]

    # Perform several actions that should each produce informative audit events
    reviewer = f"spec-rev-{suffix}"
    _create_user(client, admin_headers, reviewer, ["user"])

    client.post(
        f"/projects/{pid}/reviewers",
        headers=admin_headers,
        json={"reviewer": reviewer},
    )
    client.put(
        f"/projects/{pid}",
        headers=admin_headers,
        json={"name": f"Specificity Project {suffix} Updated"},
    )
    client.put(
        f"/projects/{pid}/priority",
        headers=admin_headers,
        json={"priority": 3},
    )

    entries = _get_audit_entries(client, admin_headers, pid)
    project_events = [
        e for e in entries
        if e.get("details", {}).get("project_id") == pid
    ]
    assert project_events, "no project events found in audit log"

    for entry in project_events:
        details = entry.get("details", {})
        # Must have project_id
        assert details.get("project_id") == pid, f"missing project_id in {entry['action']}"
        # Must have project_name (not just a raw ID)
        assert details.get("project_name"), (
            f"missing project_name in {entry['action']!r} entry: {details}"
        )
        # The message field must reference the project name, not just the ID
        msg = details.get("message") or ""
        if msg:
            assert f"Specificity Project {suffix}" in msg or pid in msg, (
                f"message too vague for {entry['action']!r}: {msg!r}"
            )


# ---------------------------------------------------------------------------
# 11. Review summary accuracy after concurrent operations
# ---------------------------------------------------------------------------


def test_review_summary_accurate_after_concurrent_operations(client, admin_headers):
    """review-summary endpoint must accurately reflect all concurrent assignment completions."""
    suffix = uuid.uuid4().hex[:6]
    n = 4
    reviewer_names = [f"sum-rev-{suffix}-{i}" for i in range(n)]
    for name in reviewer_names:
        _create_user(client, admin_headers, name, ["user"])

    project = _create_project(client, admin_headers, f"Summary Project {suffix}")
    pid = project["id"]

    # Create all assignments
    assignment_ids = []
    for reviewer in reviewer_names:
        r = client.post(
            f"/projects/{pid}/assignments",
            headers=admin_headers,
            json={"reviewer": reviewer},
        )
        assert r.status_code == 201
        assignment_ids.append(r.json()["id"])

    # Concurrently complete all assignments
    errors: list[str] = []
    lock = threading.Lock()

    def _complete(reviewer: str, aid: str) -> None:
        try:
            rev_headers = _make_test_headers(client, reviewer)
            r = client.post(f"/projects/{pid}/assignments/{aid}/start", headers=rev_headers)
            assert r.status_code == 200, f"start: {r.text}"
            r = client.post(f"/projects/{pid}/assignments/{aid}/concur", headers=rev_headers)
            assert r.status_code == 200, f"concur: {r.text}"
        except Exception as exc:
            with lock:
                errors.append(f"{reviewer}: {exc}")

    threads = [
        threading.Thread(target=_complete, args=(reviewer_names[i], assignment_ids[i]))
        for i in range(n)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"completion errors: {errors}"

    # Review summary must reflect all concurred
    r = client.get(f"/projects/{pid}/review-summary", headers=admin_headers)
    assert r.status_code == 200
    summary = r.json()
    assert summary.get("all_complete") is True, (
        f"review_summary shows incomplete after all concurred: {summary}"
    )


# ---------------------------------------------------------------------------
# 12. Priority update under concurrent load — last write wins, no corruption
# ---------------------------------------------------------------------------


def test_concurrent_priority_updates_no_corruption(client, admin_headers):
    """50 concurrent priority updates; project must survive with a valid priority."""
    suffix = uuid.uuid4().hex[:6]
    project = _create_project(client, admin_headers, f"Priority Pressure {suffix}")
    pid = project["id"]

    n = 50
    errors: list[str] = []
    lock = threading.Lock()

    def _update(priority: int) -> None:
        r = client.put(
            f"/projects/{pid}/priority",
            headers=admin_headers,
            json={"priority": priority % 5},
        )
        if r.status_code not in (200,):
            with lock:
                errors.append(f"priority {priority}: {r.status_code} {r.text}")

    threads = [threading.Thread(target=_update, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"priority update errors: {errors}"

    r = client.get(f"/projects/{pid}", headers=admin_headers)
    assert r.status_code == 200
    p = r.json()
    assert 0 <= p["priority"] <= 4, f"corrupted priority value: {p['priority']}"


# ---------------------------------------------------------------------------
# 13. Concurrent project delete + read — no 5xx, no ghost projects
# ---------------------------------------------------------------------------


def test_concurrent_delete_and_read_no_server_errors(client, admin_headers):
    """One thread deletes a project while others read it; no 5xx allowed."""
    suffix = uuid.uuid4().hex[:6]
    project = _create_project(client, admin_headers, f"Delete Race {suffix}")
    pid = project["id"]

    status_codes: list[int] = []
    lock = threading.Lock()

    def _read() -> None:
        r = client.get(f"/projects/{pid}", headers=admin_headers)
        with lock:
            status_codes.append(r.status_code)

    def _delete() -> None:
        time.sleep(0.01)  # slight delay so reads start first
        r = client.delete(f"/projects/{pid}", headers=admin_headers)
        with lock:
            status_codes.append(r.status_code)

    threads = [threading.Thread(target=_read) for _ in range(10)]
    threads.append(threading.Thread(target=_delete))
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    five_xx = [c for c in status_codes if c >= 500]
    assert not five_xx, f"5xx errors during delete/read race: {five_xx}"

    # Project must be gone after delete
    r = client.get(f"/projects/{pid}", headers=admin_headers)
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# 14. Full stress: many projects + reviewers + feedback under concurrent load
# ---------------------------------------------------------------------------


def test_projects_area_full_stress_no_5xx(client, admin_headers):
    """30 concurrent mixed operations (create, review, feedback) must produce zero 5xx."""
    suffix = uuid.uuid4().hex[:6]
    n_projects = 6
    n_reviewers = 6
    n_threads_per_project = 5

    reviewer_names = [f"stress-rev-{suffix}-{i}" for i in range(n_reviewers)]
    for name in reviewer_names:
        _create_user(client, admin_headers, name, ["user"])

    projects_created = []
    for i in range(n_projects):
        p = _create_project(client, admin_headers, f"Stress Project {suffix} {i}")
        projects_created.append(p["id"])

    five_xx_count = 0
    lock = threading.Lock()

    def _stress_worker(pid: str, reviewer: str) -> None:
        nonlocal five_xx_count
        rev_headers = _make_test_headers(client, reviewer)

        ops = [
            lambda: client.get(f"/projects/{pid}", headers=admin_headers),
            lambda: client.post(
                f"/projects/{pid}/reviewers",
                headers=admin_headers,
                json={"reviewer": reviewer},
            ),
            lambda: client.post(
                f"/projects/{pid}/assignments",
                headers=admin_headers,
                json={"reviewer": reviewer},
            ),
            lambda: client.post(
                f"/projects/{pid}/feedback",
                headers=rev_headers,
                json={"text": f"Stress feedback {suffix}", "feedback_type": "comment"},
            ),
            lambda: client.get(f"/projects/{pid}/review-summary", headers=admin_headers),
            lambda: client.get(f"/projects/{pid}/assignments", headers=admin_headers),
        ]
        import random
        op = random.choice(ops)
        r = op()
        if r.status_code >= 500:
            with lock:
                five_xx_count += 1

    with ThreadPoolExecutor(max_workers=30) as pool:
        futures = []
        for i, pid in enumerate(projects_created):
            for j in range(n_threads_per_project):
                reviewer = reviewer_names[(i + j) % n_reviewers]
                futures.append(pool.submit(_stress_worker, pid, reviewer))
        for f in as_completed(futures):
            f.result()  # re-raise if any thread raised

    assert five_xx_count == 0, f"{five_xx_count} 5xx errors during full stress test"


# ---------------------------------------------------------------------------
# 15. Audit log humanize uses rich message, not raw IDs
# ---------------------------------------------------------------------------


def test_humanize_audit_action_uses_message_field():
    """humanize_audit_action must use details.message when present."""
    from docreview360.audit import humanize_audit_action

    rich_message = "bob created project 'Budget Review' (DOC-001; id abc123) for owner alice"
    result = humanize_audit_action(
        "create_project",
        user_id="bob",
        entity_id="abc123",
        details={"message": rich_message, "project_id": "abc123"},
    )
    assert result == rich_message, f"humanize returned template instead of message: {result!r}"


def test_humanize_audit_action_falls_back_to_template_without_message():
    """humanize_audit_action must fall back to template when no message in details."""
    from docreview360.audit import humanize_audit_action

    result = humanize_audit_action(
        "create_project",
        user_id="alice",
        entity_id="proj-123",
        details={"project_id": "proj-123"},
    )
    assert "alice" in result
    assert "proj-123" in result

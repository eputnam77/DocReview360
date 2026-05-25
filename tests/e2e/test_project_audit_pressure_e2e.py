from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from playwright.sync_api import Page, expect

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_full]

_PASSWORD = "Password!1234"


def _login(page: Page, backend_url: str, username: str, password: str = "password") -> str:
    response = page.request.post(
        f"{backend_url}/token",
        form={"username": username, "password": password},
    )
    assert response.ok, f"login failed for {username}: {response.status} {response.text()}"
    token = response.json()["access_token"]
    assert token
    return token


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _create_user(
    page: Page,
    backend_url: str,
    admin_token: str,
    username: str,
    roles: list[str],
) -> None:
    response = page.request.post(
        f"{backend_url}/users",
        headers=_headers(admin_token),
        data={
            "username": username,
            "password": _PASSWORD,
            "roles": roles,
            "active": True,
        },
    )
    if response.status == 409:
        update = page.request.put(
            f"{backend_url}/users/{username}",
            headers=_headers(admin_token),
            data={"roles": roles, "active": True},
        )
        assert update.ok, f"user update failed for {username}: {update.status} {update.text()}"
        return
    assert response.status == 201, response.text()


def _ui_login(page: Page, frontend_url: str, username: str, password: str = "password") -> None:
    page.goto(f"{frontend_url}/login", wait_until="domcontentloaded")
    page.get_by_label("Username").fill(username)
    page.get_by_label("Password").fill(password)
    page.get_by_role("button", name="Sign In").click(force=True)
    page.wait_for_url(f"{frontend_url}/projects")


@pytest.mark.e2e_smoke
def test_project_area_audit_events_stay_specific_under_pressure(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
) -> None:
    suffix = uuid4().hex[:8]
    admin_token = _login(page, e2e_backend_url, "bob")
    reviewer = f"audit-reviewer-{suffix}"
    reviewer_next = f"audit-reviewer-next-{suffix}"
    temp_user = f"audit-temp-{suffix}"
    _create_user(page, e2e_backend_url, admin_token, reviewer, ["reviewer", "user"])
    _create_user(page, e2e_backend_url, admin_token, reviewer_next, ["reviewer", "user"])
    _create_user(page, e2e_backend_url, admin_token, temp_user, ["user"])

    doc_types = page.request.get(f"{e2e_backend_url}/document-types", headers=_headers(admin_token))
    assert doc_types.ok
    doc_type = doc_types.json()[0]
    phases = doc_type.get("phases") or doc_type.get("workflow") or ["draft", "review"]
    first_phase = phases[0]
    next_phase = phases[1] if len(phases) > 1 else "review"

    project_name = f"Audit Pressure Project {suffix}"
    document_number = f"AUD-{suffix}"
    create_project = page.request.post(
        f"{e2e_backend_url}/projects",
        headers=_headers(admin_token),
        data={
            "name": project_name,
            "document_number": document_number,
            "doc_type": doc_type["name"],
            "phase": first_phase,
            "user": "bob",
        },
    )
    assert create_project.status == 201, create_project.text()
    project = create_project.json()
    project_id = project["id"]

    add_reviewer = page.request.post(
        f"{e2e_backend_url}/projects/{project_id}/reviewers",
        headers=_headers(admin_token),
        data={"reviewer": reviewer},
    )
    assert add_reviewer.ok, add_reviewer.text()

    update_reviewer = page.request.put(
        f"{e2e_backend_url}/projects/{project_id}/reviewers/{reviewer}",
        headers=_headers(admin_token),
        data={"reviewer": reviewer_next},
    )
    assert update_reviewer.ok, update_reviewer.text()

    assignment = page.request.post(
        f"{e2e_backend_url}/projects/{project_id}/assignments",
        headers=_headers(admin_token),
        data={"reviewer": reviewer_next},
    )
    assert assignment.status == 201, assignment.text()
    assignment_id = assignment.json()["id"]

    reviewer_token = _login(page, e2e_backend_url, reviewer_next, _PASSWORD)
    start = page.request.post(
        f"{e2e_backend_url}/projects/{project_id}/assignments/{assignment_id}/start",
        headers=_headers(reviewer_token),
    )
    assert start.ok, start.text()

    feedback = page.request.post(
        f"{e2e_backend_url}/projects/{project_id}/feedback",
        headers=_headers(reviewer_token),
        data={
            "text": f"Audit pressure question {suffix}",
            "feedback_type": "question",
            "assignment_id": assignment_id,
            "phase": first_phase,
        },
    )
    assert feedback.status == 201, feedback.text()

    submit = page.request.post(
        f"{e2e_backend_url}/projects/{project_id}/assignments/{assignment_id}/submit",
        headers=_headers(reviewer_token),
    )
    assert submit.ok, submit.text()

    review = page.request.post(
        f"{e2e_backend_url}/projects/{project_id}/reviews",
        headers=_headers(admin_token),
        data={"comment": f"Manager review summary {suffix}", "status": "approved"},
    )
    assert review.status == 201, review.text()

    updated_name = f"{project_name} Updated"
    update_project = page.request.put(
        f"{e2e_backend_url}/projects/{project_id}",
        headers=_headers(admin_token),
        data={"name": updated_name, "phase": next_phase},
    )
    assert update_project.ok, update_project.text()

    priority = page.request.put(
        f"{e2e_backend_url}/projects/{project_id}/priority",
        headers=_headers(admin_token),
        data={"priority": 4},
    )
    assert priority.ok, priority.text()

    until = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    temporary = page.request.post(
        f"{e2e_backend_url}/projects/{project_id}/temporary",
        headers=_headers(admin_token),
        data={"user": temp_user, "until": until},
    )
    assert temporary.ok, temporary.text()

    audit = page.request.get(
        f"{e2e_backend_url}/api/audit?entity_id={project_id}",
        headers=_headers(admin_token),
    )
    assert audit.ok, audit.text()
    entries = audit.json()
    actions = {entry["action"] for entry in entries}
    assert {
        "create_project",
        "reviewer_added",
        "reviewer_updated",
        "review.assigned",
        "review.status_changed",
        "feedback.submitted",
        "review.submitted",
        "review_submitted",
        "update_project",
        "project_priority_updated",
        "project_temporary_assigned",
    }.issubset(actions)

    important_entries = [
        entry
        for entry in entries
        if entry["action"]
        in {
            "create_project",
            "reviewer_added",
            "reviewer_updated",
            "review.assigned",
            "feedback.submitted",
            "review.submitted",
            "review_submitted",
            "update_project",
            "project_priority_updated",
            "project_temporary_assigned",
        }
    ]
    assert important_entries
    for entry in important_entries:
        details = entry.get("details") or {}
        message = details.get("message") or ""
        assert updated_name in message or project_name in message
        assert document_number in message
        assert details.get("project_id") == project_id
        assert details.get("project_name") in {project_name, updated_name}

    remove_reviewer = page.request.delete(
        f"{e2e_backend_url}/projects/{project_id}/reviewers/{reviewer_next}",
        headers=_headers(admin_token),
    )
    assert remove_reviewer.ok, remove_reviewer.text()

    _ui_login(page, e2e_frontend_url, "bob")
    page.goto(f"{e2e_frontend_url}/configuration/audit-logs", wait_until="domcontentloaded")
    page.get_by_placeholder("Entity").fill(project_id)
    expect(page.get_by_text(re.compile(re.escape(document_number))).first).to_be_visible(
        timeout=10_000
    )
    expect(page.get_by_text(re.compile(re.escape(updated_name))).first).to_be_visible(
        timeout=10_000
    )

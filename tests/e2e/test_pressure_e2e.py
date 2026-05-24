from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

import pytest
from playwright.sync_api import Browser, Page, expect

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_full]

_PASSWORD = "Password!1234"


def _json_request(
    method: str,
    url: str,
    *,
    token: str | None = None,
    payload: dict[str, Any] | None = None,
) -> tuple[int, Any]:
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else None
    except HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            body = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            body = raw
        return exc.code, body


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


def _create_user(page: Page, backend_url: str, admin_token: str, username: str, roles: list[str]) -> None:
    create = page.request.post(
        f"{backend_url}/users",
        headers=_headers(admin_token),
        data={"username": username, "password": _PASSWORD, "roles": roles, "active": True},
    )
    if create.status == 409:
        update = page.request.put(
            f"{backend_url}/users/{username}",
            headers=_headers(admin_token),
            data={"roles": roles, "active": True},
        )
        assert update.ok, f"user update failed for {username}: {update.status} {update.text()}"
        return
    assert create.status == 201, f"user create failed for {username}: {create.status} {create.text()}"


def _new_actor_page(
    browser: Browser,
    frontend_url: str,
    backend_url: str,
    username: str,
    password: str,
) -> Page:
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(30_000)
    backend_literal = json.dumps(backend_url)
    page.add_init_script(
        f"""
        () => {{
          const backendUrl = {backend_literal};
          window.__DOCREVIEW360_API_BASE = backendUrl;
          try {{
            localStorage.setItem("docreview360_api_base", backendUrl);
          }} catch (_) {{}}
        }}
        """,
    )
    page.goto(f"{frontend_url}/login")
    page.get_by_label("Username").fill(username)
    page.get_by_label("Password").fill(password)
    page.get_by_role("button", name="Sign In").click(force=True)
    page.wait_for_url(f"{frontend_url}/projects")
    return page


def _assert_no_app_crash(page: Page, route: str) -> None:
    body = page.locator("body").inner_text(timeout=10_000)
    crash_markers = [
        "Application error",
        "Unhandled Runtime Error",
        "This page could not be found",
        "TypeError:",
        "ReferenceError:",
    ]
    assert not any(marker in body for marker in crash_markers), f"{route} rendered crash text: {body[:500]}"


def test_multi_role_same_project_pressure_flow(
    page: Page,
    browser: Browser,
    e2e_frontend_url: str,
    e2e_backend_url: str,
) -> None:
    """Push one project through overlapping owner, editor, reviewer, approver, and invalid-user actions."""

    suffix = uuid4().hex[:8]
    admin_token = _login(page, e2e_backend_url, "bob")
    actors = {
        "owner": f"pressure-owner-{suffix}",
        "editor": f"pressure-editor-{suffix}",
        "reviewer": f"pressure-reviewer-{suffix}",
        "approver": f"pressure-approver-{suffix}",
        "outsider": f"pressure-outsider-{suffix}",
    }
    _create_user(page, e2e_backend_url, admin_token, actors["owner"], ["user"])
    _create_user(page, e2e_backend_url, admin_token, actors["editor"], ["user"])
    _create_user(page, e2e_backend_url, admin_token, actors["reviewer"], ["reviewer", "user"])
    _create_user(page, e2e_backend_url, admin_token, actors["approver"], ["reviewer", "user"])
    _create_user(page, e2e_backend_url, admin_token, actors["outsider"], ["user"])

    owner_token = _login(page, e2e_backend_url, actors["owner"], _PASSWORD)
    editor_token = _login(page, e2e_backend_url, actors["editor"], _PASSWORD)
    reviewer_token = _login(page, e2e_backend_url, actors["reviewer"], _PASSWORD)
    approver_token = _login(page, e2e_backend_url, actors["approver"], _PASSWORD)
    outsider_token = _login(page, e2e_backend_url, actors["outsider"], _PASSWORD)

    doc_types = page.request.get(f"{e2e_backend_url}/document-types", headers=_headers(admin_token))
    assert doc_types.ok
    doc_type = doc_types.json()[0]
    phase = (doc_type.get("phases") or doc_type.get("workflow") or ["draft"])[0]

    project_resp = page.request.post(
        f"{e2e_backend_url}/projects",
        headers=_headers(admin_token),
        data={
            "id": f"pressure-project-{suffix}",
            "name": f"Pressure Project {suffix}",
            "document_number": f"PRESS-{suffix}",
            "doc_type": doc_type["name"],
            "phase": phase,
            "user": actors["owner"],
        },
    )
    assert project_resp.status == 201, project_resp.text()
    project_id = project_resp.json()["id"]

    workflow_resp = page.request.post(
        f"{e2e_backend_url}/workflows",
        headers=_headers(admin_token),
        data={"project": project_id, "phases": ["draft", "review", "approval"]},
    )
    assert workflow_resp.status == 201, workflow_resp.text()
    workflow_id = workflow_resp.json()["id"]

    document_resp = page.request.post(
        f"{e2e_backend_url}/documents/import",
        headers={"Authorization": f"Bearer {admin_token}"},
        multipart={
            "file": {
                "name": "pressure.md",
                "mimeType": "text/markdown",
                "buffer": b"# Pressure Test\n\nInitial production-like draft.",
            },
            "project": project_id,
            "user": actors["owner"],
        },
    )
    assert document_resp.status == 201, document_resp.text()
    document_id = document_resp.json()["id"]

    reviewer_resp = page.request.post(
        f"{e2e_backend_url}/projects/{project_id}/reviewers",
        headers=_headers(admin_token),
        data={"reviewer": actors["reviewer"]},
    )
    assert reviewer_resp.ok

    assignment_resp = page.request.post(
        f"{e2e_backend_url}/projects/{project_id}/assignments",
        headers=_headers(admin_token),
        data={"reviewer": actors["reviewer"]},
    )
    assert assignment_resp.status == 201, assignment_resp.text()
    assignment_id = assignment_resp.json()["id"]

    approval_resp = page.request.post(
        f"{e2e_backend_url}/approvals",
        headers=_headers(admin_token),
        data={
            "workflow": workflow_id,
            "reviewer": actors["approver"],
            "doc_id": document_id,
            "description": "Pressure approval",
        },
    )
    assert approval_resp.status == 201, approval_resp.text()
    approval_id = approval_resp.json()["id"]

    owner_page = _new_actor_page(
        browser, e2e_frontend_url, e2e_backend_url, actors["owner"], _PASSWORD
    )
    reviewer_page = _new_actor_page(
        browser, e2e_frontend_url, e2e_backend_url, actors["reviewer"], _PASSWORD
    )
    approver_page = _new_actor_page(
        browser, e2e_frontend_url, e2e_backend_url, actors["approver"], _PASSWORD
    )
    try:
        owner_page.goto(f"{e2e_frontend_url}/projects/{project_id}")
        owner_page.get_by_test_id("comments-section-toggle").click()
        owner_page.get_by_placeholder("Add a comment...").fill(f"Owner context note {suffix}")
        owner_page.get_by_role("button", name="Submit").click()
        owner_page.get_by_text(f"Owner context note {suffix}").wait_for()

        reviewer_page.goto(f"{e2e_frontend_url}/projects/{project_id}")
        expect(reviewer_page.get_by_test_id("reviewer-signoff-section-toggle")).to_be_visible()
        reviewer_page.get_by_test_id("comments-section-toggle").click()
        reviewer_page.get_by_role("button", name="Question").first.click()
        reviewer_page.get_by_placeholder("Add a question...").fill(f"Reviewer question {suffix}")
        reviewer_page.get_by_role("button", name="Submit").click()
        reviewer_page.get_by_text(f"Reviewer question {suffix}").wait_for()

        approver_page.goto(f"{e2e_frontend_url}/projects/{project_id}")
        expect(approver_page.get_by_text(re.compile(r"Pressure Project", re.I))).to_be_visible()
        _assert_no_app_crash(approver_page, "approver project detail")
    finally:
        owner_page.context.close()
        reviewer_page.context.close()
        approver_page.context.close()

    outsider_doc = page.request.get(
        f"{e2e_backend_url}/documents/{document_id}",
        headers=_headers(outsider_token),
    )
    assert outsider_doc.status == 403

    invalid_feedback = page.request.post(
        f"{e2e_backend_url}/projects/{project_id}/feedback",
        headers=_headers(reviewer_token),
        data={"text": "nonsense type should fail safely", "feedback_type": "not_a_real_type"},
    )
    assert invalid_feedback.status == 422

    def worker_call(actor: str, token: str, index: int) -> tuple[str, str, int, Any]:
        if actor == "editor":
            return (
                actor,
                "PUT document",
                *_json_request(
                    "PUT",
                    f"{e2e_backend_url}/documents/{document_id}",
                    token=token,
                    payload={"content": f"# Pressure Test\n\nEditor rapid update {index} {suffix}"},
                ),
            )
        feedback_type = "suggestion" if actor == "reviewer" else "comment"
        return (
            actor,
            "POST feedback",
            *_json_request(
                "POST",
                f"{e2e_backend_url}/projects/{project_id}/feedback",
                token=token,
                payload={
                    "text": f"{actor} concurrent feedback {index} {suffix}",
                    "feedback_type": feedback_type,
                    "tags": ["pressure", actor],
                },
            ),
        )

    jobs = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for index in range(6):
            jobs.append(pool.submit(worker_call, "owner", owner_token, index))
            jobs.append(pool.submit(worker_call, "reviewer", reviewer_token, index))
            jobs.append(pool.submit(worker_call, "editor", owner_token, index))
        jobs.append(
            pool.submit(
                lambda: (
                    "reviewer",
                    "POST assignment start",
                    *_json_request(
                        "POST",
                        f"{e2e_backend_url}/projects/{project_id}/assignments/{assignment_id}/start",
                        token=reviewer_token,
                    ),
                )
            )
        )
        jobs.append(
            pool.submit(
                lambda: (
                    "approver",
                    "POST sign initials",
                    *_json_request(
                        "POST",
                        f"{e2e_backend_url}/approvals/{approval_id}/sign-initials",
                        token=approver_token,
                        payload={"initials": "PA"},
                    ),
                )
            )
        )
        results = [job.result() for job in as_completed(jobs)]

    unexpected = [
        result
        for result in results
        if result[2] >= 500 or result[2] in {401, 404}
    ]
    assert not unexpected, f"unexpected pressure API failures: {unexpected}"

    feedback_resp = page.request.get(
        f"{e2e_backend_url}/projects/{project_id}/feedback",
        headers=_headers(admin_token),
    )
    assert feedback_resp.ok
    feedback_items = feedback_resp.json()["items"]
    assert len(feedback_items) >= 14

    document_after = page.request.get(
        f"{e2e_backend_url}/documents/{document_id}",
        headers=_headers(admin_token),
    )
    assert document_after.ok
    assert "Editor rapid update" in document_after.json()["content"]

    approval_after = page.request.get(
        f"{e2e_backend_url}/approvals/{approval_id}",
        headers=_headers(admin_token),
    )
    assert approval_after.ok
    assert approval_after.json()["state"] == "approved"


def test_admin_and_user_route_surface_does_not_crash(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
    e2e_seed_data: dict,
) -> None:
    """Sweep dashboards, tools, help, and configuration pages for route-level crashes."""

    token = _login(page, e2e_backend_url, "bob")
    page.goto(f"{e2e_frontend_url}/login")
    page.evaluate(
        """
        ([backendUrl, accessToken]) => {
          window.__DOCREVIEW360_API_BASE = backendUrl;
          localStorage.setItem("docreview360_api_base", backendUrl);
          localStorage.setItem("access_token", accessToken);
        }
        """,
        [e2e_backend_url, token],
    )

    project_id = e2e_seed_data["project"]["id"]
    admin_routes = [
        "/dashboard",
        "/dashboard/admin",
        "/dashboard/manager",
        "/dashboard/user",
        "/dashboard/settings",
        "/projects",
        "/projects/new",
        f"/projects/{project_id}",
        f"/projects/{project_id}/edit",
        "/reviews",
        "/search?q=DOC",
        "/tools",
        "/tools/checker",
        "/tools/converter",
        "/tools/document-analysis",
        "/tools/document-processor",
        "/tools/document-quality",
        "/help",
        "/docs",
        "/about",
        "/profile",
        "/configuration",
        "/configuration/permissions",
        "/configuration/user-management",
        "/configuration/workflows",
        "/configuration/workflows/new",
        "/configuration/phases",
        "/configuration/document-types",
        "/configuration/templates",
        "/configuration/templates/new",
        "/configuration/templates/new-email",
        "/configuration/integrations",
        "/configuration/plugin-marketplace",
        "/configuration/branding",
        "/configuration/audit-logs",
    ]

    page_errors: list[str] = []
    server_errors: list[str] = []
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))
    page.on(
        "response",
        lambda response: server_errors.append(f"{response.status} {response.url}")
        if response.url.startswith(e2e_backend_url) and response.status >= 500
        else None,
    )

    for route in admin_routes:
        response = page.goto(f"{e2e_frontend_url}{route}", wait_until="domcontentloaded")
        assert response is not None and response.status < 500, f"{route} returned {response.status if response else 'none'}"
        page.wait_for_timeout(350)
        _assert_no_app_crash(page, route)

    assert not page_errors, f"route sweep page errors: {page_errors[:5]}"
    assert not server_errors, f"route sweep backend 5xx responses: {server_errors[:10]}"

    user_token = _login(page, e2e_backend_url, "alice")
    page.goto(f"{e2e_frontend_url}/login")
    page.evaluate(
        """
        ([backendUrl, accessToken]) => {
          window.__DOCREVIEW360_API_BASE = backendUrl;
          localStorage.setItem("docreview360_api_base", backendUrl);
          localStorage.setItem("access_token", accessToken);
        }
        """,
        [e2e_backend_url, user_token],
    )
    for route in ["/dashboard/user", "/projects", f"/projects/{project_id}", "/tools", "/help", "/profile"]:
        response = page.goto(f"{e2e_frontend_url}{route}", wait_until="domcontentloaded")
        assert response is not None and response.status < 500, f"user route {route} failed"
        page.wait_for_timeout(250)
        _assert_no_app_crash(page, route)

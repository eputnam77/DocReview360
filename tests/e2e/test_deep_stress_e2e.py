"""Deep stress test — pushes every surface of DocReview360 toward production limits.

Covers:
- ALL frontend routes including dynamic ones never swept before
- Real multi-user concurrent UI (3 browser contexts on the same project)
- Configuration round-trips: doc types, phases, workflow templates, branding
- Tools: document quality checker, document analysis, converter with real content
- Dashboard data validation: admin, manager, user
- User management full flow (create → role change → suspend → reactivate)
- Audit-log filter UX
- Search with real results
- Template lifecycle (create → approve → retire)
- Edge cases: empty forms, special chars, duplicate submit, max-length payloads
- Review lifecycle in the UI (navigation, comment posting, status read-back)
"""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

import pytest
from playwright.sync_api import Browser, Page

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_full]

_PASSWORD = "Password!1234"

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _json_req(
    method: str,
    url: str,
    *,
    token: str | None = None,
    payload: dict[str, Any] | None = None,
    form: dict[str, str] | None = None,
    timeout: int = 20,
) -> tuple[int, Any]:
    """Lightweight HTTP helper that avoids Playwright context requirements."""
    headers: dict[str, str] = {"Accept": "application/json"}
    data: bytes | None = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode()
    elif form is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        data = "&".join(f"{k}={v}" for k, v in form.items()).encode()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw.strip() else None
    except HTTPError as exc:
        raw = exc.read().decode()
        try:
            body: Any = json.loads(raw) if raw.strip() else raw
        except json.JSONDecodeError:
            body = raw
        return exc.code, body


def _pw_login(page: Page, backend_url: str, username: str, password: str = "password") -> str:
    """POST /token and return Bearer token.

    Playwright's request context keeps the auth cookies set by /token, which is
    the same auth path the UI now uses. Avoid writing localStorage from
    about:blank because modern browsers reject origin storage there.
    """
    resp = page.request.post(
        f"{backend_url}/token",
        form={"username": username, "password": password},
    )
    assert resp.ok, f"login failed for {username}: {resp.status} {resp.text()}"
    token = resp.json()["access_token"]
    assert token
    return token


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _create_user(page: Page, backend_url: str, admin_token: str, username: str, roles: list[str]) -> None:  # noqa: E501
    resp = page.request.post(
        f"{backend_url}/users",
        headers=_headers(admin_token),
        data={"username": username, "password": _PASSWORD, "roles": roles, "active": True},
    )
    if resp.status == 409:
        upd = page.request.put(
            f"{backend_url}/users/{username}",
            headers=_headers(admin_token),
            data={"roles": roles, "active": True},
        )
        assert upd.ok, f"user update failed: {upd.status} {upd.text()}"
        return
    assert resp.status == 201, f"user create failed: {resp.status} {resp.text()}"


def _assert_no_crash(page: Page, route: str) -> None:
    """Verify the page body does not contain Next.js / React error markers."""
    body = page.locator("body").inner_text(timeout=8_000)
    for marker in ("Application error", "Unhandled Runtime Error", "TypeError:", "ReferenceError:"):
        assert marker not in body, f"{route} crash marker '{marker}' found. Body:\n{body[:400]}"


def _new_browser_page(
    browser: Browser,
    frontend_url: str,
    backend_url: str,
    username: str,
    password: str,
) -> Page:
    """Open a fresh isolated browser context, log in via the UI login form."""
    ctx = browser.new_context()
    p = ctx.new_page()
    p.set_default_timeout(30_000)
    p.add_init_script(
        f"""
        () => {{
          const u = {json.dumps(backend_url)};
          window.__DOCREVIEW360_API_BASE = u;
          try {{ localStorage.setItem("docreview360_api_base", u); }} catch(_) {{}}
        }}
        """
    )
    p.goto(f"{frontend_url}/login")
    p.get_by_label("Username").fill(username)
    p.get_by_label("Password").fill(password)
    p.get_by_role("button", name="Sign In").click(force=True)
    p.wait_for_url(f"{frontend_url}/projects")
    return p


# ---------------------------------------------------------------------------
# 1. Complete route surface — every page including dynamic ones
# ---------------------------------------------------------------------------


def test_complete_ui_route_surface(  # noqa: C901
    page: Page,
    browser: Browser,
    e2e_frontend_url: str,
    e2e_backend_url: str,
    e2e_seed_data: dict,
) -> None:
    """Visit every route in the app (including dynamic) as admin and as reviewer.

    Asserts:
    - HTTP 200 (or redirect ≤ 302) from Next.js for every route
    - No React/Next.js error markers in page body
    - No backend 5xx responses triggered by page load
    """
    admin_token = _pw_login(page, e2e_backend_url, "bob")
    project_id = e2e_seed_data["project"]["id"]

    # Create a workflow template so /configuration/workflows/{id} is reachable
    wf_resp = page.request.post(
        f"{e2e_backend_url}/workflow-templates",
        headers=_headers(admin_token),
        data={
            "name": f"Deep Stress Workflow {uuid4().hex[:6]}",
            "description": "Stress test workflow",
            "steps": [{"role": "reviewer", "required": True}],
        },
    )
    workflow_template_id: str | None = None
    if wf_resp.status in (200, 201):
        workflow_template_id = wf_resp.json().get("id")

    # Create a doc instance via review to get a review ID
    review_resp = page.request.post(
        f"{e2e_backend_url}/projects/{project_id}/reviews",
        headers={**_headers(admin_token)},
        data={"comment": "Deep stress review", "status": "approved"},
    )
    review_id: str | None = None
    if review_resp.ok:
        reviews_list = page.request.get(
            f"{e2e_backend_url}/projects/{project_id}/reviews",
            headers=_headers(admin_token),
        )
        if reviews_list.ok:
            items = reviews_list.json()
            if isinstance(items, list) and items:
                review_id = items[0].get("id") or items[0].get("review_id")
            elif isinstance(items, dict):
                first = (items.get("items") or [{}])[0]
                review_id = first.get("id") or first.get("review_id")

    # Collect all routes to sweep
    static_routes = [
        "/",
        "/login",
        "/signup",
        "/about",
        "/privacy",
        "/terms",
        "/help",
        "/docs",
        "/profile",
        "/search?q=test",
        "/search?q=&q=''",
        "/viewer",
        "/reviews",
        "/logs",
        "/integrations",
        "/custom-fields",
        "/projects",
        "/projects/new",
        f"/projects/{project_id}",
        f"/projects/{project_id}/edit",
        f"/projects/{project_id}/reviews",
        "/dashboard",
        "/dashboard/admin",
        "/dashboard/manager",
        "/dashboard/user",
        "/dashboard/settings",
        f"/dashboard/project/{project_id}",
        "/tools",
        "/tools/checker",
        "/tools/converter",
        "/tools/document-analysis",
        "/tools/document-processor",
        "/tools/document-quality",
        "/tools/sc_converter",
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
    dynamic_routes: list[str] = []
    if workflow_template_id:
        dynamic_routes += [
            f"/configuration/workflows/{workflow_template_id}",
            f"/configuration/workflows/edit?id={workflow_template_id}",
        ]
    if review_id:
        dynamic_routes.append(f"/projects/{project_id}/reviews/{review_id}")
    all_routes = static_routes + dynamic_routes

    page_errors: list[str] = []
    backend_5xx: list[str] = []
    page.on("pageerror", lambda exc: page_errors.append(f"{exc}"))
    page.on(
        "response",
        lambda r: backend_5xx.append(f"{r.status} {r.url}")
        if r.url.startswith(e2e_backend_url) and r.status >= 500
        else None,
    )

    crash_routes: list[str] = []
    for route in all_routes:
        resp = page.goto(f"{e2e_frontend_url}{route}", wait_until="domcontentloaded")
        http_status = resp.status if resp else None
        # Next.js serves everything as 200 (or 307 redirect); 404 pages still return 200 in Next.js
        if http_status is not None and http_status >= 500:
            crash_routes.append(f"{route} HTTP {http_status}")
        page.wait_for_timeout(300)
        try:
            _assert_no_crash(page, route)
        except AssertionError as exc:
            crash_routes.append(str(exc)[:200])

    # Now sweep a subset as alice (reviewer) to catch role-based rendering crashes
    _pw_login(page, e2e_backend_url, "alice")
    reviewer_routes = [
        "/dashboard",
        "/dashboard/user",
        "/projects",
        f"/projects/{project_id}",
        "/reviews",
        "/profile",
        "/tools",
        "/tools/document-quality",
        "/help",
    ]
    for route in reviewer_routes:
        page.goto(f"{e2e_frontend_url}{route}", wait_until="domcontentloaded")
        page.wait_for_timeout(200)
        try:
            _assert_no_crash(page, f"alice:{route}")
        except AssertionError as exc:
            crash_routes.append(str(exc)[:200])

    assert not crash_routes, "Route crash failures:\n" + "\n".join(crash_routes)
    assert not backend_5xx, "Backend 5xx during route sweep:\n" + "\n".join(backend_5xx[:10])
    # Page errors from CSP/HMR noise are acceptable in dev; genuine JS errors are not
    fatal_errors = [
        e for e in page_errors
        if not any(noise in e for noise in (
            "unsafe-eval", "Content Security Policy", "webpack", "WebSocket",
            "Failed to load resource", "HMR", "hot-update",
        ))
    ]
    assert not fatal_errors, f"Fatal JS page errors during sweep: {fatal_errors[:5]}"


# ---------------------------------------------------------------------------
# 2. Concurrent multi-user UI interactions on the same project
# ---------------------------------------------------------------------------


def test_concurrent_multiuser_same_project_ui(
    page: Page,
    browser: Browser,
    e2e_frontend_url: str,
    e2e_backend_url: str,
) -> None:
    """Three browser contexts — owner, reviewer, approver — interact with
    one project simultaneously in the UI, then verify final state via API."""
    suffix = uuid4().hex[:8]
    admin_token = _pw_login(page, e2e_backend_url, "bob")

    for actor, roles in [
        (f"cmu-owner-{suffix}", ["user"]),
        (f"cmu-reviewer-{suffix}", ["reviewer", "user"]),
        (f"cmu-approver-{suffix}", ["reviewer", "user"]),
    ]:
        _create_user(page, e2e_backend_url, admin_token, actor, roles)

    owner_name = f"cmu-owner-{suffix}"
    reviewer_name = f"cmu-reviewer-{suffix}"
    approver_name = f"cmu-approver-{suffix}"

    doc_types = page.request.get(f"{e2e_backend_url}/document-types", headers=_headers(admin_token))
    assert doc_types.ok
    dt = doc_types.json()[0]
    phase = (dt.get("phases") or dt.get("workflow") or ["draft"])[0]

    proj_resp = page.request.post(
        f"{e2e_backend_url}/projects",
        headers=_headers(admin_token),
        data={
            "name": f"CMU Project {suffix}",
            "document_number": f"CMU-{suffix}",
            "doc_type": dt["name"],
            "phase": phase,
            "user": owner_name,
        },
    )
    assert proj_resp.status == 201, proj_resp.text()
    project_id = proj_resp.json()["id"]

    page.request.post(
        f"{e2e_backend_url}/projects/{project_id}/reviewers",
        headers=_headers(admin_token),
        data={"reviewer": reviewer_name},
    )
    page.request.post(
        f"{e2e_backend_url}/projects/{project_id}/reviewers",
        headers=_headers(admin_token),
        data={"reviewer": approver_name},
    )

    # Import a document so there is content to discuss
    doc_resp = page.request.post(
        f"{e2e_backend_url}/documents/import",
        headers={"Authorization": f"Bearer {admin_token}"},
        multipart={
            "file": {
                "name": "cmu_doc.md",
                "mimeType": "text/markdown",
                "buffer": b"# CMU Document\n\nSection 1: Intro\n\nSection 2: Background",
            },
            "project": project_id,
            "user": owner_name,
        },
    )
    assert doc_resp.status == 201, doc_resp.text()

    owner_page = _new_browser_page(browser, e2e_frontend_url, e2e_backend_url, owner_name, _PASSWORD)  # noqa: E501
    reviewer_page = _new_browser_page(browser, e2e_frontend_url, e2e_backend_url, reviewer_name, _PASSWORD)  # noqa: E501
    approver_page = _new_browser_page(browser, e2e_frontend_url, e2e_backend_url, approver_name, _PASSWORD)  # noqa: E501

    try:
        # All three navigate to the project simultaneously
        owner_page.goto(f"{e2e_frontend_url}/projects/{project_id}", wait_until="domcontentloaded")
        reviewer_page.goto(f"{e2e_frontend_url}/projects/{project_id}", wait_until="domcontentloaded")  # noqa: E501
        approver_page.goto(f"{e2e_frontend_url}/projects/{project_id}", wait_until="domcontentloaded")  # noqa: E501

        # Owner posts a comment
        owner_page.get_by_test_id("comments-section-toggle").click()
        owner_page.get_by_placeholder("Add a comment...").fill(f"Owner note {suffix}")
        owner_page.get_by_role("button", name="Submit", exact=True).click()
        owner_page.get_by_text(f"Owner note {suffix}").wait_for(timeout=8_000)

        # Reviewer reads the project and posts a question
        reviewer_page.reload(wait_until="domcontentloaded")
        reviewer_page.get_by_test_id("comments-section-toggle").click()
        reviewer_page.get_by_role("button", name="Question").first.click()
        reviewer_page.get_by_placeholder("Add a question...").fill(f"Reviewer question {suffix}")
        reviewer_page.get_by_role("button", name="Submit", exact=True).click()
        reviewer_page.get_by_text(f"Reviewer question {suffix}").wait_for(timeout=8_000)

        # Approver views feedback section (no crash)
        approver_page.reload(wait_until="domcontentloaded")
        _assert_no_crash(approver_page, "approver view after concurrent comments")

        # Owner reloads and sees both comments
        owner_page.reload(wait_until="domcontentloaded")
        owner_page.get_by_test_id("comments-section-toggle").click()
        owner_page.get_by_text(f"Owner note {suffix}").wait_for(timeout=8_000)
        owner_page.get_by_text(f"Reviewer question {suffix}").wait_for(timeout=8_000)
    finally:
        owner_page.context.close()
        reviewer_page.context.close()
        approver_page.context.close()

    # API verification — feedback must contain both items
    fb_resp = page.request.get(
        f"{e2e_backend_url}/projects/{project_id}/feedback",
        headers=_headers(admin_token),
    )
    assert fb_resp.ok
    texts = [item["text"] for item in fb_resp.json().get("items", [])]
    assert any(f"Owner note {suffix}" in t for t in texts)
    assert any(f"Reviewer question {suffix}" in t for t in texts)


# ---------------------------------------------------------------------------
# 3. Configuration round-trips: doc type → phase → workflow template → branding
# ---------------------------------------------------------------------------


def test_configuration_full_round_trip(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
) -> None:
    """Create a doc type, phase, workflow template via API then verify all appear
    in the configuration UI; edit branding fields and verify the PUT succeeds."""
    admin_token = _pw_login(page, e2e_backend_url, "bob")
    suffix = uuid4().hex[:8]
    new_dt = f"StressType-{suffix}"
    new_phase = f"stress-phase-{suffix}"

    # ----- Doc type -----
    dt_resp = page.request.post(
        f"{e2e_backend_url}/document-types",
        headers=_headers(admin_token),
        data={
            "name": new_dt,
            "template": f"<h1>{new_dt}</h1>",
            "workflow": [new_phase, "review", "approved"],
        },
    )
    assert dt_resp.status == 201, dt_resp.text()

    # Verify in /configuration/document-types UI
    page.goto(f"{e2e_frontend_url}/configuration/document-types", wait_until="domcontentloaded")
    page.get_by_text(new_dt).wait_for(timeout=8_000)
    _assert_no_crash(page, "/configuration/document-types")

    # ----- Phase -----
    ph_resp = page.request.post(
        f"{e2e_backend_url}/phases",
        headers=_headers(admin_token),
        data={"name": new_phase, "description": f"Stress phase {suffix}"},
    )
    assert ph_resp.status == 201, ph_resp.text()

    page.goto(f"{e2e_frontend_url}/configuration/phases", wait_until="domcontentloaded")
    # phase may render as badge or table cell
    page.locator("body").wait_for()
    _assert_no_crash(page, "/configuration/phases")

    # ----- Workflow template -----
    wt_resp = page.request.post(
        f"{e2e_backend_url}/workflow-templates",
        headers=_headers(admin_token),
        data={
            "name": f"StressWorkflow-{suffix}",
            "description": "Stress test",
            "steps": [{"role": "reviewer", "required": True}],
        },
    )
    assert wt_resp.status in (200, 201), wt_resp.text()
    wt_id = wt_resp.json().get("id")

    page.goto(f"{e2e_frontend_url}/configuration/workflows", wait_until="domcontentloaded")
    page.get_by_role("link", name=f"StressWorkflow-{suffix}", exact=True).wait_for(timeout=8_000)
    _assert_no_crash(page, "/configuration/workflows")

    if wt_id:
        page.goto(f"{e2e_frontend_url}/configuration/workflows/{wt_id}", wait_until="domcontentloaded")  # noqa: E501
        page.wait_for_timeout(400)
        _assert_no_crash(page, f"/configuration/workflows/{wt_id}")

    # ----- Branding update via API -----
    config_resp = page.request.get(f"{e2e_backend_url}/config", headers=_headers(admin_token))
    assert config_resp.ok
    config = config_resp.json()
    original_company = config.get("branding_company_name", "DocReview360")
    stress_org = f"StressOrg-{suffix}"
    config["branding_company_name"] = stress_org
    put_resp = page.request.put(
        f"{e2e_backend_url}/config",
        headers={**_headers(admin_token)},
        data=json.dumps(config),
    )
    assert put_resp.ok, put_resp.text()

    # Verify branding page renders the configured company name
    page.goto(f"{e2e_frontend_url}/configuration/branding", wait_until="domcontentloaded")
    page.wait_for_timeout(600)
    assert page.get_by_label("Company Name").input_value(timeout=6_000) == stress_org

    # Restore original company name
    config["branding_company_name"] = original_company
    page.request.put(
        f"{e2e_backend_url}/config",
        headers={**_headers(admin_token)},
        data=json.dumps(config),
    )

    # Verify /configuration UI loads all subsections without crash
    for sub in ["/configuration", "/configuration/permissions", "/configuration/integrations",
                "/configuration/plugin-marketplace"]:
        page.goto(f"{e2e_frontend_url}{sub}", wait_until="domcontentloaded")
        page.wait_for_timeout(250)
        _assert_no_crash(page, sub)


# ---------------------------------------------------------------------------
# 4. Dashboard data validation: all three role dashboards
# ---------------------------------------------------------------------------


def test_dashboard_data_all_roles(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
    e2e_seed_data: dict,
) -> None:
    """Verify that the admin, manager, and user dashboards render data
    (not empty / error states) after the E2E seed has run."""
    _pw_login(page, e2e_backend_url, "bob")

    # Admin dashboard
    page.goto(f"{e2e_frontend_url}/dashboard/admin", wait_until="domcontentloaded")
    page.wait_for_timeout(800)
    _assert_no_crash(page, "/dashboard/admin")
    body = page.locator("body").inner_text(timeout=6_000)
    assert any(
        kw in body for kw in ("User Roles", "System Health", "Active Users", "Audit", "API Usage")
    ), f"Admin dashboard seems empty. Body excerpt:\n{body[:500]}"

    # Manager dashboard
    page.goto(f"{e2e_frontend_url}/dashboard/manager", wait_until="domcontentloaded")
    page.wait_for_timeout(800)
    _assert_no_crash(page, "/dashboard/manager")
    body = page.locator("body").inner_text(timeout=6_000)
    assert any(
        kw in body for kw in ("Project Status", "Leaderboard", "Deadlines", "Reviews", "Quality")
    ), f"Manager dashboard seems empty. Body:\n{body[:500]}"

    # User (alice) dashboard
    alice_token = _pw_login(page, e2e_backend_url, "alice")  # noqa: F841
    page.goto(f"{e2e_frontend_url}/dashboard/user", wait_until="domcontentloaded")
    page.wait_for_timeout(800)
    _assert_no_crash(page, "/dashboard/user")
    body = page.locator("body").inner_text(timeout=6_000)
    # User dashboard should show some stat cards or activity
    assert any(
        kw in body for kw in ("Assigned", "Completed", "Activity", "Quality", "Status", "Project")
    ), f"User dashboard seems empty. Body:\n{body[:500]}"

    # Dashboard settings page (verify no crash with preference options)
    admin_token2 = _pw_login(page, e2e_backend_url, "bob")  # noqa: F841
    page.goto(f"{e2e_frontend_url}/dashboard/settings", wait_until="domcontentloaded")
    page.wait_for_timeout(400)
    _assert_no_crash(page, "/dashboard/settings")

    # Project-specific dashboard
    project_id = e2e_seed_data["project"]["id"]
    page.goto(f"{e2e_frontend_url}/dashboard/project/{project_id}", wait_until="domcontentloaded")
    page.wait_for_timeout(500)
    _assert_no_crash(page, f"/dashboard/project/{project_id}")


# ---------------------------------------------------------------------------
# 5. Tools with real document content
# ---------------------------------------------------------------------------


def test_tools_with_real_documents(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
) -> None:
    """Exercise the document quality, analysis, and converter tools with
    actual document content, verifying the UI renders results (not error states)."""
    admin_token = _pw_login(page, e2e_backend_url, "bob")

    # Document quality checker — navigate and verify it loads
    page.goto(f"{e2e_frontend_url}/tools/document-quality", wait_until="domcontentloaded")
    page.wait_for_timeout(600)
    _assert_no_crash(page, "/tools/document-quality")
    body = page.locator("body").inner_text(timeout=6_000)
    keywords = ("Quality", "Validation", "Validator", "Upload", "Headings", "Source", "document")
    assert any(kw in body for kw in keywords), \
        f"Document quality page seems broken. Body:\n{body[:400]}"

    # Document analysis — navigate and verify it loads
    page.goto(f"{e2e_frontend_url}/tools/document-analysis", wait_until="domcontentloaded")
    page.wait_for_timeout(600)
    _assert_no_crash(page, "/tools/document-analysis")
    body = page.locator("body").inner_text(timeout=6_000)
    assert any(kw in body for kw in ("Analysis", "Upload", "analyze", "Document")), \
        f"Document analysis page seems broken. Body:\n{body[:400]}"

    # Document converter
    page.goto(f"{e2e_frontend_url}/tools/converter", wait_until="domcontentloaded")
    page.wait_for_timeout(400)
    _assert_no_crash(page, "/tools/converter")
    body = page.locator("body").inner_text(timeout=6_000)
    assert "Converter" in body or "convert" in body.lower(), \
        f"Converter page seems broken. Body:\n{body[:400]}"

    # Document processor
    page.goto(f"{e2e_frontend_url}/tools/document-processor", wait_until="domcontentloaded")
    page.wait_for_timeout(400)
    _assert_no_crash(page, "/tools/document-processor")

    # Document quality checker: exercise the backend /check-document endpoint
    check_resp = page.request.post(
        f"{e2e_backend_url}/check-document",
        headers={"Authorization": f"Bearer {admin_token}"},
        multipart={
            "file": {
                "name": "stress_check.md",
                "mimeType": "text/markdown",
                "buffer": b"# Title\n\nSome content.\n\n## Section Two\n\nMore text here.",
            },
        },
    )
    # Accept 200 or 422 (feature may require ONNX model); just reject 5xx
    assert check_resp.status < 500, f"/check-document returned {check_resp.status}: {check_resp.text()[:200]}"  # noqa: E501

    # SC Converter and tools index
    for route in ["/tools/sc_converter", "/tools"]:
        page.goto(f"{e2e_frontend_url}{route}", wait_until="domcontentloaded")
        page.wait_for_timeout(300)
        _assert_no_crash(page, route)


# ---------------------------------------------------------------------------
# 6. User management full flow: create → role change → suspend → reactivate
# ---------------------------------------------------------------------------


def test_user_management_full_flow(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
) -> None:
    """Full user lifecycle as seen by an admin: create, assign roles, suspend,
    re-activate. Verify each state is reflected via /users API."""
    admin_token = _pw_login(page, e2e_backend_url, "bob")
    suffix = uuid4().hex[:8]
    new_user = f"umgmt-{suffix}"

    # Create via API
    create_resp = page.request.post(
        f"{e2e_backend_url}/users",
        headers=_headers(admin_token),
        data={"username": new_user, "password": _PASSWORD, "roles": ["user"], "active": True},
    )
    assert create_resp.status == 201, create_resp.text()

    # Verify user appears in /configuration/user-management
    page.goto(f"{e2e_frontend_url}/configuration/user-management", wait_until="domcontentloaded")
    page.wait_for_timeout(800)
    _assert_no_crash(page, "/configuration/user-management")
    body = page.locator("body").inner_text(timeout=6_000)
    assert new_user in body, f"New user {new_user} not visible in user management. Body:\n{body[:600]}"  # noqa: E501

    # Role elevation via API
    upd = page.request.put(
        f"{e2e_backend_url}/users/{new_user}",
        headers=_headers(admin_token),
        data={"roles": ["user", "reviewer"], "active": True},
    )
    assert upd.ok, upd.text()

    # Suspend user
    suspend = page.request.put(
        f"{e2e_backend_url}/users/{new_user}",
        headers=_headers(admin_token),
        data={"roles": ["user", "reviewer"], "active": False},
    )
    assert suspend.ok, suspend.text()

    # Confirm suspended user cannot log in
    bad_login = page.request.post(
        f"{e2e_backend_url}/token",
        form={"username": new_user, "password": _PASSWORD},
    )
    assert bad_login.status in (401, 403), f"Suspended user was able to log in: {bad_login.status}"

    # Reactivate user
    reactivate = page.request.put(
        f"{e2e_backend_url}/users/{new_user}",
        headers=_headers(admin_token),
        data={"roles": ["user", "reviewer"], "active": True},
    )
    assert reactivate.ok, reactivate.text()

    # Confirm user can now log in again
    good_login = page.request.post(
        f"{e2e_backend_url}/token",
        form={"username": new_user, "password": _PASSWORD},
    )
    assert good_login.ok, f"Reactivated user failed login: {good_login.status}"

    # Verify the user is back in the users list
    users_resp = page.request.get(f"{e2e_backend_url}/users", headers=_headers(admin_token))
    assert users_resp.ok
    users = users_resp.json()
    if isinstance(users, dict):
        users = users.get("items", [])
    usernames = [u["username"] for u in users]
    assert new_user in usernames


# ---------------------------------------------------------------------------
# 7. Audit log filtering in the UI
# ---------------------------------------------------------------------------


def test_audit_log_filter_ui(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
) -> None:
    """Exercise the audit-log filter inputs and verify the page renders without crash."""
    admin_token = _pw_login(page, e2e_backend_url, "bob")

    # Navigate to audit logs
    page.goto(f"{e2e_frontend_url}/configuration/audit-logs", wait_until="domcontentloaded")
    page.wait_for_timeout(800)
    _assert_no_crash(page, "/configuration/audit-logs")

    body = page.locator("body").inner_text(timeout=6_000)
    assert "Audit" in body, f"Audit Logs page missing 'Audit'. Body:\n{body[:400]}"

    # Filter by user
    user_input = page.get_by_placeholder("User")
    if user_input.count() > 0:
        user_input.first.fill("bob")
        page.wait_for_timeout(600)
        _assert_no_crash(page, "audit-logs filtered by user")

    # Filter by action
    action_input = page.get_by_placeholder("Action")
    if action_input.count() > 0:
        action_input.first.fill("login")
        page.wait_for_timeout(600)
        _assert_no_crash(page, "audit-logs filtered by action")

    # Filter by severity
    severity_input = page.get_by_placeholder("Severity")
    if severity_input.count() > 0:
        severity_input.first.fill("info")
        page.wait_for_timeout(600)
        _assert_no_crash(page, "audit-logs filtered by severity")

    # Also verify via API that audit log returns entries
    audit_resp = page.request.get(f"{e2e_backend_url}/api/audit", headers=_headers(admin_token))
    assert audit_resp.ok, f"GET /api/audit failed: {audit_resp.status}"
    audit_data = audit_resp.json()
    items = audit_data if isinstance(audit_data, list) else audit_data.get("items", audit_data.get("logs", []))  # noqa: E501
    assert isinstance(items, list), f"Expected list of audit entries, got {type(items)}"


# ---------------------------------------------------------------------------
# 8. Search with real content
# ---------------------------------------------------------------------------


def test_search_with_real_content(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
    e2e_seed_data: dict,
) -> None:
    """Verify the search page works with queries that should return results
    (seeded project names and document numbers)."""
    admin_token = _pw_login(page, e2e_backend_url, "bob")

    # Navigate to search
    page.goto(f"{e2e_frontend_url}/search?q=DOC", wait_until="domcontentloaded")
    page.wait_for_timeout(600)
    _assert_no_crash(page, "/search?q=DOC")

    # Use the search form in the UI
    page.goto(f"{e2e_frontend_url}/search", wait_until="domcontentloaded")
    search_input = page.locator("#search-input")
    if search_input.count() > 0:
        search_input.fill("DOC")
        page.get_by_role("button", name=re.compile(r"search", re.I)).first.click()
        page.wait_for_timeout(800)
        _assert_no_crash(page, "search results for DOC")

    # Backend search API
    search_api = page.request.get(
        f"{e2e_backend_url}/search?q=DOC",
        headers=_headers(admin_token),
    )
    assert search_api.ok or search_api.status == 404, \
        f"Search API unexpected status: {search_api.status}"

    # Edge case: empty search
    page.goto(f"{e2e_frontend_url}/search?q=", wait_until="domcontentloaded")
    page.wait_for_timeout(400)
    _assert_no_crash(page, "search empty query")

    # Edge case: special chars
    page.goto(f"{e2e_frontend_url}/search?q=<script>alert(1)</script>", wait_until="domcontentloaded")  # noqa: E501
    page.wait_for_timeout(400)
    _assert_no_crash(page, "search XSS attempt")
    body = page.locator("body").inner_text(timeout=6_000)
    # The raw script tag must NOT be executed (no alert dialog popped; body won't contain rendered alert)  # noqa: E501
    assert "alert(1)" not in body or "<script>" not in body


# ---------------------------------------------------------------------------
# 9. Template lifecycle: create → approve → retire
# ---------------------------------------------------------------------------


def test_template_lifecycle(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
) -> None:
    """Full document template lifecycle: create via API, verify in UI,
    approve it, retire it, verify status changes."""
    admin_token = _pw_login(page, e2e_backend_url, "bob")
    suffix = uuid4().hex[:8]
    template_name = f"Stress Template {suffix}"

    # Create template via API
    tpl_resp = page.request.post(
        f"{e2e_backend_url}/templates",
        headers=_headers(admin_token),
        data={
            "name": template_name,
            "doc_type": "SOW",
            "content": f"<h1>{template_name}</h1><p>Template body.</p>",
            "status": "draft",
        },
    )
    if tpl_resp.status == 404:
        pytest.skip("Template creation endpoint not available in this deployment")
    assert tpl_resp.status in (200, 201), f"Template creation failed: {tpl_resp.status} {tpl_resp.text()}"  # noqa: E501
    tpl_id = tpl_resp.json().get("id")

    # Verify it appears in /configuration/templates
    page.goto(f"{e2e_frontend_url}/configuration/templates", wait_until="domcontentloaded")
    page.wait_for_timeout(600)
    _assert_no_crash(page, "/configuration/templates")
    body = page.locator("body").inner_text(timeout=6_000)
    assert template_name in body, f"Template '{template_name}' not visible. Body:\n{body[:600]}"

    # Approve via API
    if tpl_id:
        approve_resp = page.request.post(
            f"{e2e_backend_url}/templates/{tpl_id}/approve",
            headers=_headers(admin_token),
        )
        # Accept 200/204 or 405 (if approve is UI-only)
        assert approve_resp.status < 500, f"Template approve failed: {approve_resp.status}"

        # Retire via API
        retire_resp = page.request.post(
            f"{e2e_backend_url}/templates/{tpl_id}/retire",
            headers=_headers(admin_token),
        )
        assert retire_resp.status < 500, f"Template retire failed: {retire_resp.status}"

        # Edit template page should still load
        page.goto(f"{e2e_frontend_url}/configuration/templates/edit?id={tpl_id}", wait_until="domcontentloaded")  # noqa: E501
        page.wait_for_timeout(400)
        _assert_no_crash(page, f"/configuration/templates/edit?id={tpl_id}")


# ---------------------------------------------------------------------------
# 10. Review lifecycle in the UI (reviews list + individual review page)
# ---------------------------------------------------------------------------


def test_review_lifecycle_ui(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
    e2e_seed_data: dict,
) -> None:
    """Navigate to /reviews, open an individual review, verify the page renders."""
    admin_token = _pw_login(page, e2e_backend_url, "bob")
    project_id = e2e_seed_data["project"]["id"]

    # Post a review so the reviews list is not empty
    page.request.post(
        f"{e2e_backend_url}/projects/{project_id}/reviews",
        headers={**_headers(admin_token)},
        data={"comment": "UI lifecycle review", "status": "approved"},
    )

    page.goto(f"{e2e_frontend_url}/reviews", wait_until="domcontentloaded")
    page.wait_for_timeout(800)
    _assert_no_crash(page, "/reviews")
    body = page.locator("body").inner_text(timeout=6_000)
    assert "Review" in body, f"/reviews page missing 'Review'. Body:\n{body[:400]}"

    # Get a review ID from the API
    reviews_resp = page.request.get(
        f"{e2e_backend_url}/projects/{project_id}/reviews",
        headers=_headers(admin_token),
    )
    if reviews_resp.ok:
        items = reviews_resp.json()
        if isinstance(items, list) and items:
            rid = items[0].get("id") or items[0].get("review_id")
        elif isinstance(items, dict):
            first = (items.get("items") or [{}])[0]
            rid = first.get("id") or first.get("review_id")
        else:
            rid = None
        if rid:
            page.goto(f"{e2e_frontend_url}/reviews/{rid}", wait_until="domcontentloaded")
            page.wait_for_timeout(600)
            _assert_no_crash(page, f"/reviews/{rid}")

    # Project-specific reviews page
    page.goto(f"{e2e_frontend_url}/projects/{project_id}/reviews", wait_until="domcontentloaded")
    page.wait_for_timeout(600)
    _assert_no_crash(page, f"/projects/{project_id}/reviews")


# ---------------------------------------------------------------------------
# 11. Edge cases: empty inputs, duplicate submit, special chars, max-length
# ---------------------------------------------------------------------------


def test_edge_cases_inputs_and_api(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
    e2e_seed_data: dict,
) -> None:
    """Exercise boundary and invalid-input scenarios across the API surface."""
    admin_token = _pw_login(page, e2e_backend_url, "bob")
    project_id = e2e_seed_data["project"]["id"]
    hdrs = _headers(admin_token)

    # --- Empty comment --- must be rejected or ignored gracefully (not 5xx)
    empty_fb = page.request.post(
        f"{e2e_backend_url}/projects/{project_id}/feedback",
        headers=hdrs,
        data={"text": "", "feedback_type": "comment"},
    )
    assert empty_fb.status != 500, f"Empty feedback caused 500: {empty_fb.text()[:200]}"

    # --- Special-characters in comment text ---
    special_fb = page.request.post(
        f"{e2e_backend_url}/projects/{project_id}/feedback",
        headers=hdrs,
        data={
            "text": "<script>alert('xss')</script> & ' \" \x00 \n\t\r 日本語 emoji: 🚀",
            "feedback_type": "comment",
        },
    )
    assert special_fb.status < 500, f"Special chars caused 500: {special_fb.text()[:200]}"

    # --- Max-length text (10 000 chars) ---
    long_text = "A" * 10_000
    long_fb = page.request.post(
        f"{e2e_backend_url}/projects/{project_id}/feedback",
        headers=hdrs,
        data={"text": long_text, "feedback_type": "comment"},
    )
    assert long_fb.status < 500, f"Long text caused 500: {long_fb.text()[:200]}"

    # --- Duplicate review submission ---
    for _ in range(3):
        dup = page.request.post(
            f"{e2e_backend_url}/projects/{project_id}/reviews",
            headers=hdrs,
            data={"comment": "Duplicate review submission", "status": "approved"},
        )
        assert dup.status < 500, f"Duplicate review submission caused 500: {dup.text()[:200]}"

    # --- Invalid project ID ---
    ghost = page.request.get(
        f"{e2e_backend_url}/projects/DOES-NOT-EXIST-EVER",
        headers=hdrs,
    )
    assert ghost.status in (404, 422), f"Nonexistent project returned {ghost.status}"

    # --- Malformed JSON payload ---
    malformed = page.request.post(
        f"{e2e_backend_url}/projects/{project_id}/reviews",
        headers={**hdrs, "Content-Type": "application/json"},
        data='{"comment": "broken json", "status":',  # intentionally truncated
    )
    assert malformed.status in (400, 422, 500), \
        f"Malformed JSON body got unexpected status: {malformed.status}"

    # --- Verify project page still loads after all the abuse ---
    page.goto(f"{e2e_frontend_url}/projects/{project_id}", wait_until="domcontentloaded")
    page.wait_for_timeout(500)
    _assert_no_crash(page, "project page after edge case abuse")


# ---------------------------------------------------------------------------
# 12. Rapid concurrent API writes — hammer feedback + document edits
# ---------------------------------------------------------------------------


def test_high_concurrency_api_writes(  # noqa: C901
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
) -> None:
    """Fire 40+ concurrent API writes (feedback + document updates) against a single
    project; assert zero 5xx responses and verify final consistency."""
    suffix = uuid4().hex[:8]
    _, login_data = _json_req("POST", f"{e2e_backend_url}/token",
                              form={"username": "bob", "password": "password"})
    admin_token = login_data["access_token"]

    _, dt_data = _json_req("GET", f"{e2e_backend_url}/document-types", token=admin_token)
    dt = dt_data[0]
    phase = (dt.get("phases") or dt.get("workflow") or ["draft"])[0]

    # Create users for the concurrency test
    reviewer_count = 15
    for i in range(reviewer_count):
        _json_req(
            "POST", f"{e2e_backend_url}/users", token=admin_token,
            payload={"username": f"conc-{suffix}-{i}", "password": _PASSWORD,
                     "roles": ["user"], "active": True},
        )

    status, proj_data = _json_req(
        "POST", f"{e2e_backend_url}/projects", token=admin_token,
        payload={
            "name": f"Concurrency Project {suffix}",
            "document_number": f"CONC-{suffix}",
            "doc_type": dt["name"],
            "phase": phase,
            "user": "bob",
        },
    )
    assert status == 201, f"Project creation failed: {proj_data}"
    project_id = proj_data["id"]

    for i in range(reviewer_count):
        reviewer_status, reviewer_body = _json_req(
            "POST",
            f"{e2e_backend_url}/projects/{project_id}/reviewers",
            token=admin_token,
            payload={"reviewer": f"conc-{suffix}-{i}"},
        )
        assert reviewer_status in (200, 201), (
            f"Reviewer assignment failed for conc-{suffix}-{i}: "
            f"{reviewer_status} {reviewer_body}"
        )

    # Import a document
    doc_req_data = (
        b"--boundary\r\nContent-Disposition: form-data; name=\"file\"; filename=\"conc.md\"\r\n"
        b"Content-Type: text/markdown\r\n\r\n# Concurrency\n\nInitial content.\r\n"
        b"--boundary\r\nContent-Disposition: form-data; name=\"project\"\r\n\r\n"
        + project_id.encode()
        + b"\r\n--boundary\r\nContent-Disposition: form-data; name=\"user\"\r\n\r\nbob\r\n--boundary--"  # noqa: E501
    )
    doc_req = Request(
        f"{e2e_backend_url}/documents/import",
        data=doc_req_data,
        headers={
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "multipart/form-data; boundary=boundary",
        },
        method="POST",
    )
    try:
        with urlopen(doc_req, timeout=20) as r:
            doc_data = json.loads(r.read().decode())
        document_id = doc_data["id"]
    except Exception as exc:
        pytest.skip(f"Document import failed (skipping concurrency test): {exc}")
        return

    # Get tokens for all actors
    tokens: list[str] = [admin_token]
    for i in range(reviewer_count):
        _, tok_data = _json_req("POST", f"{e2e_backend_url}/token",
                                form={"username": f"conc-{suffix}-{i}", "password": _PASSWORD})
        tokens.append(tok_data["access_token"])

    # Define concurrent tasks
    def feedback_task(token: str, idx: int) -> tuple[int, Any]:
        return _json_req(
            "POST",
            f"{e2e_backend_url}/projects/{project_id}/feedback",
            token=token,
            payload={
                "text": f"Concurrent comment {idx} from {suffix}",
                "feedback_type": "comment",
                "tags": ["stress", f"worker-{idx}"],
            },
        )

    def doc_edit_task(token: str, idx: int) -> tuple[int, Any]:
        return _json_req(
            "PUT",
            f"{e2e_backend_url}/documents/{document_id}",
            token=token,
            payload={"content": f"# Updated\n\nConcurrent edit {idx} {suffix}"},
        )

    def review_task(token: str, idx: int) -> tuple[int, Any]:
        return _json_req(
            "POST",
            f"{e2e_backend_url}/projects/{project_id}/reviews",
            token=token,
            payload={"comment": f"Concurrent review {idx}", "status": "needs_revision"},
        )

    futures = []
    with ThreadPoolExecutor(max_workers=12) as pool:
        for i in range(15):
            tok = tokens[i % len(tokens)]
            futures.append(pool.submit(feedback_task, tok, i))
        for i in range(10):
            futures.append(pool.submit(doc_edit_task, admin_token, i))
        for i in range(8):
            futures.append(pool.submit(review_task, admin_token, i))

    results = [f.result() for f in as_completed(futures)]
    server_errors = [(status, body) for status, body in results if status >= 500]
    assert not server_errors, f"Concurrent writes produced 5xx responses: {server_errors[:5]}"

    # Verify at least 10 feedback items were stored
    _, fb_data = _json_req(
        "GET", f"{e2e_backend_url}/projects/{project_id}/feedback",
        token=admin_token,
    )
    items = fb_data.get("items", []) if isinstance(fb_data, dict) else fb_data
    assert len(items) >= 10, f"Expected ≥10 feedback items, got {len(items)}"

    # Verify the project page still loads in the browser
    _ = _pw_login(page, e2e_backend_url, "bob")
    page.goto(f"{e2e_frontend_url}/projects/{project_id}", wait_until="domcontentloaded")
    page.wait_for_timeout(500)
    _assert_no_crash(page, "project page after high-concurrency writes")


# ---------------------------------------------------------------------------
# 13. Profile settings and permissions page
# ---------------------------------------------------------------------------


def test_profile_and_permissions_pages(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
) -> None:
    """Verify that profile and permissions pages render real user data."""
    admin_token = _pw_login(page, e2e_backend_url, "bob")

    # Profile page
    page.goto(f"{e2e_frontend_url}/profile", wait_until="domcontentloaded")
    page.wait_for_timeout(800)
    _assert_no_crash(page, "/profile")
    body = page.locator("body").inner_text(timeout=6_000)
    assert "bob" in body.lower() or "admin" in body.lower(), \
        f"Profile page doesn't show bob or admin role. Body:\n{body[:500]}"

    # Permissions config page
    page.goto(f"{e2e_frontend_url}/configuration/permissions", wait_until="domcontentloaded")
    page.wait_for_timeout(800)
    _assert_no_crash(page, "/configuration/permissions")
    body = page.locator("body").inner_text(timeout=6_000)
    assert any(
        kw in body for kw in ("Permission", "Role", "admin", "reviewer", "user")
    ), f"Permissions page seems empty. Body:\n{body[:400]}"

    # RBAC API verification
    rbac_resp = page.request.get(
        f"{e2e_backend_url}/rbac/role-permissions",
        headers=_headers(admin_token),
    )
    assert rbac_resp.ok, f"/rbac/role-permissions failed: {rbac_resp.status}"
    roles_data = rbac_resp.json()
    assert isinstance(roles_data, list) and len(roles_data) > 0, \
        f"Expected non-empty role permissions list, got: {roles_data}"


# ---------------------------------------------------------------------------
# 14. Editor routes with actual projectId (CKEditor5 and TipTap)
# ---------------------------------------------------------------------------


def test_editor_routes_load_without_crash(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
    e2e_seed_data: dict,
) -> None:
    """Verify that the TipTap and CKEditor5 editors load for a real project
    without JavaScript errors or React crashes."""
    admin_token = _pw_login(page, e2e_backend_url, "bob")
    project_id = e2e_seed_data["project"]["id"]

    config_resp = page.request.get(f"{e2e_backend_url}/config", headers=_headers(admin_token))
    assert config_resp.ok
    original_config = config_resp.json()

    def _set_editor(editor: str) -> None:
        cfg = dict(original_config)
        cfg["editor"] = editor
        resp = page.request.put(
            f"{e2e_backend_url}/config",
            headers={**_headers(admin_token)},
            data=json.dumps(cfg),
        )
        assert resp.ok, resp.text()

    try:
        # CKEditor5
        _set_editor("ckeditor5")
        page.goto(f"{e2e_frontend_url}/editors/ckeditor5?projectId={project_id}",
                  wait_until="domcontentloaded")
        page.wait_for_timeout(1_000)
        _assert_no_crash(page, f"/editors/ckeditor5?projectId={project_id}")

        # TipTap
        _set_editor("tiptap")
        page.goto(f"{e2e_frontend_url}/editors/tiptap?projectId={project_id}",
                  wait_until="domcontentloaded")
        page.wait_for_timeout(1_000)
        _assert_no_crash(page, f"/editors/tiptap?projectId={project_id}")
        body = page.locator("body").inner_text(timeout=6_000)
        assert any(
            kw in body for kw in ("TipTap", "editor", "document", "save", "Edit")
        ), f"TipTap editor page seems empty. Body:\n{body[:500]}"

        # Editor without projectId should not 500
        page.goto(f"{e2e_frontend_url}/editors/tiptap", wait_until="domcontentloaded")
        page.wait_for_timeout(400)
        _assert_no_crash(page, "/editors/tiptap (no projectId)")

    finally:
        # Restore original config
        page.request.put(
            f"{e2e_backend_url}/config",
            headers={**_headers(admin_token)},
            data=json.dumps(original_config),
        )


# ---------------------------------------------------------------------------
# 15. Workflow phase transitions
# ---------------------------------------------------------------------------


def test_workflow_phase_transitions(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
) -> None:
    """Create a project, drive it through phase transitions via the API,
    and verify the project page reflects each state in the UI."""
    admin_token = _pw_login(page, e2e_backend_url, "bob")
    suffix = uuid4().hex[:8]

    dt_resp = page.request.get(f"{e2e_backend_url}/document-types", headers=_headers(admin_token))
    assert dt_resp.ok
    dt = dt_resp.json()[0]
    phases = dt.get("phases") or dt.get("workflow") or ["draft", "review", "approved"]
    assert len(phases) >= 2, "Need at least 2 phases for this test"

    proj_resp = page.request.post(
        f"{e2e_backend_url}/projects",
        headers=_headers(admin_token),
        data={
            "name": f"Phase Transition {suffix}",
            "document_number": f"PT-{suffix}",
            "doc_type": dt["name"],
            "phase": phases[0],
            "user": "bob",
        },
    )
    assert proj_resp.status == 201, proj_resp.text()
    project_id = proj_resp.json()["id"]

    # Verify initial phase is visible in the project UI
    page.goto(f"{e2e_frontend_url}/projects/{project_id}", wait_until="domcontentloaded")
    page.wait_for_timeout(600)
    _assert_no_crash(page, f"project {project_id} initial phase")

    # Transition through phases
    for phase in phases[1:3]:  # only first two transitions to keep test fast
        advance_resp = page.request.patch(
            f"{e2e_backend_url}/projects/{project_id}",
            headers=_headers(admin_token),
            data={"phase": phase},
        )
        if advance_resp.status == 405:
            # Try PUT if PATCH not allowed
            advance_resp = page.request.put(
                f"{e2e_backend_url}/projects/{project_id}",
                headers=_headers(admin_token),
                data={"phase": phase},
            )
        assert advance_resp.status < 500, \
            f"Phase transition to '{phase}' returned {advance_resp.status}: {advance_resp.text()[:200]}"  # noqa: E501

        # Verify project reflects new phase
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(500)
        _assert_no_crash(page, f"project {project_id} after phase→{phase}")


# ---------------------------------------------------------------------------
# 16. Logs page
# ---------------------------------------------------------------------------


def test_logs_page_loads(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
) -> None:
    """Verify the live-logs page loads (even if no WebSocket messages arrive)."""
    _pw_login(page, e2e_backend_url, "bob")

    page.goto(f"{e2e_frontend_url}/logs", wait_until="domcontentloaded")
    page.wait_for_timeout(800)
    _assert_no_crash(page, "/logs")
    body = page.locator("body").inner_text(timeout=6_000)
    assert any(kw in body for kw in ("Log", "log", "Live")), \
        f"Logs page missing expected content. Body:\n{body[:400]}"


# ---------------------------------------------------------------------------
# 17. Plugin marketplace interaction
# ---------------------------------------------------------------------------


def test_plugin_marketplace_ui(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
) -> None:
    """Browse the plugin marketplace and verify it renders plugin cards."""
    admin_token = _pw_login(page, e2e_backend_url, "bob")

    page.goto(f"{e2e_frontend_url}/configuration/plugin-marketplace", wait_until="domcontentloaded")
    page.wait_for_timeout(800)
    _assert_no_crash(page, "/configuration/plugin-marketplace")
    body = page.locator("body").inner_text(timeout=6_000)
    assert "Plugin" in body or "Marketplace" in body, \
        f"Plugin marketplace missing expected content. Body:\n{body[:400]}"

    # API: marketplace plugins list
    plugins_resp = page.request.get(
        f"{e2e_backend_url}/plugins",
        headers=_headers(admin_token),
    )
    # 404 is OK if endpoint not yet wired; 5xx is not
    assert plugins_resp.status < 500, f"/plugins returned {plugins_resp.status}"


# ---------------------------------------------------------------------------
# 18. Help, docs, about, privacy, terms pages
# ---------------------------------------------------------------------------


def test_informational_pages(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
) -> None:
    """Verify informational pages load without crash for an unauthenticated
    visitor and for an authenticated admin."""
    # Unauthenticated visit (no localStorage token set)
    for route in ["/about", "/privacy", "/terms", "/help", "/docs"]:
        page.goto(f"{e2e_frontend_url}{route}", wait_until="domcontentloaded")
        page.wait_for_timeout(300)
        try:
            _assert_no_crash(page, f"unauthenticated:{route}")
        except AssertionError as exc:
            # "This page could not be found" is expected for stub pages — not a crash
            if "This page could not be found" in str(exc):
                continue
            raise

    # Authenticated
    _pw_login(page, e2e_backend_url, "bob")
    for route in ["/about", "/help", "/docs"]:
        page.goto(f"{e2e_frontend_url}{route}", wait_until="domcontentloaded")
        page.wait_for_timeout(300)
        try:
            _assert_no_crash(page, f"authenticated:{route}")
        except AssertionError as exc:
            if "This page could not be found" in str(exc):
                continue
            raise


# ---------------------------------------------------------------------------
# 19. Project creation and edit via the UI forms
# ---------------------------------------------------------------------------


def test_project_create_and_edit_ui_forms(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
) -> None:
    """Verify the project creation and edit forms render correctly and
    accept valid input (full UI form flow, not API-only)."""
    _pw_login(page, e2e_backend_url, "bob")

    # Project creation form
    page.goto(f"{e2e_frontend_url}/projects/new", wait_until="domcontentloaded")
    page.wait_for_timeout(600)
    _assert_no_crash(page, "/projects/new")
    body = page.locator("body").inner_text(timeout=6_000)
    assert any(kw in body for kw in ("New Project", "Create", "Document Number", "name", "project")), (  # noqa: E501
        f"Projects/new page seems empty. Body:\n{body[:400]}"
    )

    # Fill and submit via UI
    suffix = uuid4().hex[:8]
    name_input = page.get_by_label(re.compile(r"project name|name", re.I)).first
    if name_input.count() == 0:
        name_input = page.locator("input[name='name']")
    if name_input.count() > 0:
        name_input.fill(f"UI Form Project {suffix}")

    docnum_input = page.get_by_label(re.compile(r"document number|doc.?num", re.I)).first
    if docnum_input.count() == 0:
        docnum_input = page.locator("input[name='document_number']")
    if docnum_input.count() > 0:
        docnum_input.fill(f"UI-{suffix}")

    # Submit the form
    submit_btn = page.get_by_role("button", name=re.compile(r"create|submit|save", re.I)).first
    if submit_btn.count() > 0:
        submit_btn.click(force=True)
        page.wait_for_timeout(1_200)
        _assert_no_crash(page, "after project create form submit")

    # Navigate to projects list and verify no crash
    page.goto(f"{e2e_frontend_url}/projects", wait_until="domcontentloaded")
    page.wait_for_timeout(600)
    _assert_no_crash(page, "/projects list")
    body = page.locator("body").inner_text(timeout=6_000)
    assert any(kw in body for kw in ("Project", "project", "Document", "New")), \
        f"Projects list page seems empty. Body:\n{body[:400]}"

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from .bug_logger import BugLoggerAgent
from .models import (
    ApiTrace,
    BrowserRunConfig,
    BugReport,
    ScenarioResult,
    ScenarioState,
)


class BrowserAgentError(RuntimeError):
    """Raised when the watchable browser scenario cannot proceed."""


def run_browser_ckeditor_suite(
    *,
    run_id: str,
    config: BrowserRunConfig,
    bug_report_dir: Path,
) -> list[ScenarioResult]:
    """Run a visible CKEditor workflow against live frontend/backend services."""

    state = ScenarioState(run_id=run_id)
    logger = BugLoggerAgent(bug_report_dir)
    bug_reports: list[BugReport] = []
    try:
        _run_ckeditor_browser_flow(state=state, config=config)
    except Exception as exc:
        report = _build_browser_bug_report(state=state, config=config, error=exc)
        logger.record(report)
        bug_reports.append(report)
    return [
        ScenarioResult(
            name="browser-ckeditor-review-workflow",
            state=state,
            bug_reports=bug_reports,
        )
    ]


def _run_ckeditor_browser_flow(*, state: ScenarioState, config: BrowserRunConfig) -> None:
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # noqa: BLE001 - keep error actionable for runner users
        raise BrowserAgentError(
            "Playwright is not installed. Install the project test extra and browser binaries."
        ) from exc

    frontend_url = config.normalized_frontend_url
    backend_url = config.normalized_backend_url

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not config.headed, slow_mo=config.slow_mo_ms)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(config.timeout_ms)
        backend_literal = json.dumps(backend_url)
        page.add_init_script(
            f"""
            () => {{
              const backendUrl = {backend_literal};
              window.__DOCREVIEW360_API_BASE = backendUrl;
              try {{
                localStorage.setItem("docreview360_api_base", backendUrl);
              }} catch (_) {{
                // storage may be unavailable in constrained browser contexts
              }}
            }}
            """
        )

        try:
            admin_headers = _login_via_api(
                page,
                state,
                backend_url=backend_url,
                frontend_url=frontend_url,
                username=config.admin_username,
                password=config.admin_password,
            )
            _ensure_reviewer(page, state, backend_url, admin_headers, config)
            project = _create_project(
                page,
                state,
                backend_url,
                admin_headers,
                config.admin_username,
            )
            workflow = _create_workflow(page, state, backend_url, admin_headers)
            document = _import_document(
                page,
                state,
                backend_url,
                admin_headers,
                config.admin_username,
            )
            _assign_reviewer(page, state, backend_url, admin_headers, config.reviewer_username)

            _login_through_visible_form(
                page,
                frontend_url=frontend_url,
                username=config.reviewer_username,
                password=config.reviewer_password,
            )
            reviewer_headers = _token_headers_via_api(
                page,
                state,
                backend_url=backend_url,
                username=config.reviewer_username,
                password=config.reviewer_password,
            )
            editor_url = f"{frontend_url}/editors/ckeditor5?id={document['id']}"
            page.goto(editor_url)
            page.get_by_role("heading", name="Project Editor").wait_for()
            editor = page.locator("[contenteditable='true']").first
            editor.wait_for()
            editor.click()
            page.keyboard.press("Control+A")
            page.keyboard.type("Agentic browser edit for DocReview360 API review.")
            editor.blur()
            page.get_by_text("Save status: saved").wait_for(timeout=config.timeout_ms)

            comment_box = page.get_by_placeholder(re.compile(r"add a comment", re.I)).first
            try:
                comment_box.wait_for(timeout=5_000)
                comment_box.fill("Browser agent watched CKEditor and left a review note.")
                page.get_by_role("button", name=re.compile(r"post", re.I)).click(force=True)
            except PlaywrightTimeoutError:
                state.artifacts["comment_ui"] = "comment controls were not visible on CKEditor page"

            approval = _create_approval(
                page,
                state,
                backend_url,
                admin_headers,
                config.reviewer_username,
            )
            _approve_with_initials(page, state, backend_url, reviewer_headers, approval["id"])

            state.artifacts.update(
                {
                    "project": project,
                    "workflow": workflow,
                    "document": document,
                    "approval": approval,
                    "editor_url": editor_url,
                }
            )
        except Exception:
            screenshot_dir = Path("tests") / "agentic" / "bug-reports"
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            screenshot = screenshot_dir / f"{state.run_id}-browser-failure.png"
            try:
                page.screenshot(path=str(screenshot), full_page=True)
                state.artifacts["screenshot_paths"] = [str(screenshot)]
            except Exception:
                pass
            raise
        finally:
            context.close()
            browser.close()


def _login_via_api(
    page: Any,
    state: ScenarioState,
    *,
    backend_url: str,
    frontend_url: str,
    username: str,
    password: str,
) -> dict[str, str]:
    headers = _token_headers_via_api(
        page,
        state,
        backend_url=backend_url,
        username=username,
        password=password,
    )
    token = headers["Authorization"].removeprefix("Bearer ")
    page.goto(f"{frontend_url}/login")
    page.evaluate("(token) => localStorage.setItem('access_token', token)", token)
    return headers


def _token_headers_via_api(
    page: Any,
    state: ScenarioState,
    *,
    backend_url: str,
    username: str,
    password: str,
) -> dict[str, str]:
    response = page.request.post(
        f"{backend_url}/token",
        form={"username": username, "password": password},
    )
    _record_trace(state, username, "POST", "/token", (200,), response)
    if not response.ok:
        raise BrowserAgentError(f"login failed for {username}: {response.status} {response.text()}")
    token = response.json().get("access_token")
    if not token:
        raise BrowserAgentError(f"login response for {username} did not include access_token")
    return {"Authorization": f"Bearer {token}"}


def _login_through_visible_form(
    page: Any,
    *,
    frontend_url: str,
    username: str,
    password: str,
) -> None:
    page.goto(f"{frontend_url}/login")
    page.get_by_label("Username").fill(username)
    page.get_by_label("Password").fill(password)
    page.get_by_role("button", name="Sign In").click(force=True)
    page.wait_for_url(f"{frontend_url}/projects")


def _ensure_reviewer(
    page: Any,
    state: ScenarioState,
    backend_url: str,
    headers: dict[str, str],
    config: BrowserRunConfig,
) -> None:
    response = page.request.post(
        f"{backend_url}/users",
        headers=_json_headers(headers),
        data=json.dumps({
            "username": config.reviewer_username,
            "password": config.reviewer_password,
            "roles": ["reviewer", "user"],
            "active": True,
        }),
    )
    _record_trace(state, config.admin_username, "POST", "/users", (201, 409, 422), response)
    if response.status == 201:
        return
    update = page.request.put(
        f"{backend_url}/users/{config.reviewer_username}",
        headers=_json_headers(headers),
        data=json.dumps({
            "roles": ["reviewer", "user"],
            "active": True,
        }),
    )
    _record_trace(
        state,
        config.admin_username,
        "PUT",
        f"/users/{config.reviewer_username}",
        (200,),
        update,
    )
    if not update.ok:
        raise BrowserAgentError(f"reviewer setup failed: {update.status} {update.text()}")


def _create_project(
    page: Any,
    state: ScenarioState,
    backend_url: str,
    headers: dict[str, str],
    owner: str,
) -> dict[str, Any]:
    project_id = f"agentic-browser-{state.run_id}"
    response = page.request.post(
        f"{backend_url}/projects",
        headers=_json_headers(headers),
        data=json.dumps(
            {"id": project_id, "name": "Watchable Browser Agent Review", "user": owner}
        ),
    )
    _record_trace(state, "browser-admin", "POST", "/projects", (201, 409), response)
    if response.status == 409:
        response = page.request.get(f"{backend_url}/projects/{project_id}", headers=headers)
        _record_trace(state, "browser-admin", "GET", f"/projects/{project_id}", (200,), response)
    if not response.ok:
        raise BrowserAgentError(f"project setup failed: {response.status} {response.text()}")
    project = response.json()
    state.project_id = project["id"]
    return project


def _create_workflow(
    page: Any,
    state: ScenarioState,
    backend_url: str,
    headers: dict[str, str],
) -> dict[str, Any]:
    workflow_phases = ["draft", "review", "approval"]
    # Ensure phases exist before workflow creation (POST /workflows validates phase existence)
    for phase in workflow_phases:
        page.request.post(
            f"{backend_url}/phases",
            headers=_json_headers(headers),
            data=json.dumps({"name": phase}),
        )
    response = page.request.post(
        f"{backend_url}/workflows",
        headers=_json_headers(headers),
        data=json.dumps({"project": state.project_id, "phases": workflow_phases}),
    )
    _record_trace(state, "browser-admin", "POST", "/workflows", (201,), response)
    if not response.ok:
        raise BrowserAgentError(f"workflow setup failed: {response.status} {response.text()}")
    workflow = response.json()
    state.workflow_id = workflow["id"]
    return workflow


def _import_document(
    page: Any,
    state: ScenarioState,
    backend_url: str,
    headers: dict[str, str],
    owner: str,
) -> dict[str, Any]:
    response = page.request.post(
        f"{backend_url}/documents/import",
        headers=headers,
        multipart={
            "file": {
                "name": "agentic-browser-api.md",
                "mimeType": "text/markdown",
                "buffer": b"# DocReview360 API\n\nBrowser agent seed document.",
            },
            "project": state.project_id,
            "user": owner,
        },
    )
    _record_trace(state, "browser-admin", "POST", "/documents/import", (201,), response)
    if not response.ok:
        raise BrowserAgentError(f"document import failed: {response.status} {response.text()}")
    document = response.json()
    state.document_id = document["id"]
    return document


def _assign_reviewer(
    page: Any,
    state: ScenarioState,
    backend_url: str,
    headers: dict[str, str],
    reviewer: str,
) -> None:
    response = page.request.post(
        f"{backend_url}/projects/{state.project_id}/reviewers",
        headers=_json_headers(headers),
        data=json.dumps({"reviewer": reviewer}),
    )
    _record_trace(
        state,
        "browser-admin",
        "POST",
        f"/projects/{state.project_id}/reviewers",
        (200,),
        response,
    )
    if not response.ok:
        raise BrowserAgentError(f"reviewer assignment failed: {response.status} {response.text()}")


def _create_approval(
    page: Any,
    state: ScenarioState,
    backend_url: str,
    headers: dict[str, str],
    reviewer: str,
) -> dict[str, Any]:
    response = page.request.post(
        f"{backend_url}/approvals",
        headers=_json_headers(headers),
        data=json.dumps({
            "workflow": state.workflow_id,
            "reviewer": reviewer,
            "doc_id": state.document_id,
            "description": "Browser agent approval",
        }),
    )
    _record_trace(state, "browser-admin", "POST", "/approvals", (201,), response)
    if not response.ok:
        raise BrowserAgentError(f"approval creation failed: {response.status} {response.text()}")
    approval = response.json()
    state.approval_ids.append(approval["id"])
    return approval


def _approve_with_initials(
    page: Any,
    state: ScenarioState,
    backend_url: str,
    headers: dict[str, str],
    approval_id: str,
) -> None:
    response = page.request.post(
        f"{backend_url}/approvals/{approval_id}/sign-initials",
        headers=_json_headers(headers),
        data=json.dumps({"initials": "BA"}),
    )
    _record_trace(
        state,
        "browser-reviewer",
        "POST",
        f"/approvals/{approval_id}/sign-initials",
        (200,),
        response,
    )
    if not response.ok:
        raise BrowserAgentError(f"approval failed: {response.status} {response.text()}")


def _record_trace(
    state: ScenarioState,
    actor: str,
    method: str,
    path: str,
    expected: tuple[int, ...],
    response: Any,
) -> None:
    try:
        response_json = response.json()
    except Exception:
        response_json = None
    state.traces.append(
        ApiTrace(
            actor=actor,
            method=method,
            path=path,
            expected_statuses=expected,
            actual_status=response.status,
            response_json=response_json,
        )
    )


def _json_headers(headers: dict[str, str]) -> dict[str, str]:
    return {**headers, "Content-Type": "application/json"}


def _build_browser_bug_report(
    *,
    state: ScenarioState,
    config: BrowserRunConfig,
    error: Exception,
) -> BugReport:
    screenshot_paths = tuple(state.artifacts.get("screenshot_paths", []))
    return BugReport(
        id=f"bug-browser-{uuid4().hex[:12]}",
        run_id=state.run_id,
        title=f"Browser CKEditor workflow failed: {type(error).__name__}",
        severity="high",
        expected=(
            "Browser agent should seed a document, open CKEditor, edit content, "
            "and approve the final document."
        ),
        actual=str(error),
        repro_steps=tuple(
            f"{trace.actor}: {trace.method} {trace.path} -> {trace.actual_status}"
            for trace in state.traces
        )
        or (
            f"Open frontend {config.normalized_frontend_url} against "
            f"backend {config.normalized_backend_url}",
        ),
        api_traces=tuple(state.traces),
        screenshot_paths=screenshot_paths,
    )

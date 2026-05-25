from __future__ import annotations

import re
from uuid import uuid4

import pytest
from playwright.sync_api import Page, expect

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_full]


def _login(
    page: Page,
    frontend_url: str,
    backend_url: str,
    username: str = "bob",
    password: str = "password",
) -> dict[str, str]:
    token_resp = page.request.post(
        f"{backend_url}/token",
        form={"username": username, "password": password},
    )
    assert token_resp.ok, f"Expected /token success for {username}, got {token_resp.status}"
    access_token = token_resp.json().get("access_token")
    assert access_token, "Expected access_token in /token response"
    page.goto(f"{frontend_url}/login")
    page.evaluate("(token) => localStorage.setItem('access_token', token)", access_token)
    page.wait_for_function("() => !!localStorage.getItem('access_token')")
    return {"Authorization": f"Bearer {access_token}"}


def _json_headers(headers: dict[str, str]) -> dict[str, str]:
    return {**headers, "Content-Type": "application/json"}


def _create_project_with_document(
    page: Page,
    backend_url: str,
    headers: dict[str, str],
    suffix: str,
) -> tuple[str, str]:
    doc_types_resp = page.request.get(f"{backend_url}/document-types", headers=headers)
    assert doc_types_resp.ok
    doc_type = doc_types_resp.json()[0]
    phase = (doc_type.get("phases") or doc_type.get("workflow") or ["draft"])[0]

    project_resp = page.request.post(
        f"{backend_url}/projects",
        headers=_json_headers(headers),
        data={
            "name": f"Editor Stress Project {suffix}",
            "document_number": f"EDIT-{suffix}",
            "doc_type": doc_type["name"],
            "phase": phase,
            "user": "bob",
        },
    )
    assert project_resp.status == 201, project_resp.text()
    project_id = project_resp.json()["id"]

    document_resp = page.request.post(
        f"{backend_url}/documents/import",
        headers=headers,
        multipart={
            "file": {
                "name": "editor-stress.md",
                "mimeType": "text/markdown",
                "buffer": b"# Editor Stress\n\nInitial draft for toolbar pressure.",
            },
            "project": project_id,
            "user": "bob",
        },
    )
    assert document_resp.status == 201, document_resp.text()
    return project_id, document_resp.json()["id"]


def _revision_count(
    page: Page,
    backend_url: str,
    headers: dict[str, str],
    document_id: str,
) -> int:
    revisions_resp = page.request.get(
        f"{backend_url}/documents/{document_id}/revisions",
        headers=headers,
    )
    assert revisions_resp.ok, revisions_resp.text()
    return len(revisions_resp.json())


def _wait_for_revision_growth(
    page: Page,
    backend_url: str,
    headers: dict[str, str],
    document_id: str,
    baseline: int,
) -> None:
    for _ in range(30):
        if _revision_count(page, backend_url, headers, document_id) > baseline:
            return
        page.wait_for_timeout(250)
    pytest.fail(f"Expected a new revision for document {document_id}")


def _assert_no_app_crash(page: Page, route: str) -> None:
    body = page.locator("body").inner_text(timeout=10_000)
    crash_markers = [
        "Application error",
        "Unhandled Runtime Error",
        "TypeError:",
        "ReferenceError:",
    ]
    assert not any(marker in body for marker in crash_markers), (
        f"{route} rendered crash text: {body[:500]}"
    )


def _click_ckeditor_toolbar_button(page: Page, index: int, label: str) -> None:
    buttons = page.locator(".ck-toolbar button.ck-button")
    count = buttons.count()
    assert count > index, f"Expected CKEditor {label} button at index {index}, found {count}"
    buttons.nth(index).click(force=True)


@pytest.mark.e2e_smoke
def test_editor_toolbar_pressure_and_revision_persistence(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
) -> None:
    """Drive both production editors through dense formatting and save paths."""

    headers = _login(page, e2e_frontend_url, e2e_backend_url)
    suffix = uuid4().hex[:8]
    project_id, document_id = _create_project_with_document(
        page,
        e2e_backend_url,
        headers,
        suffix,
    )

    page_errors: list[str] = []
    backend_5xx: list[str] = []
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))
    page.on(
        "response",
        lambda response: backend_5xx.append(f"{response.status} {response.url}")
        if response.url.startswith(e2e_backend_url) and response.status >= 500
        else None,
    )

    tiptap_baseline = _revision_count(page, e2e_backend_url, headers, document_id)
    page.goto(f"{e2e_frontend_url}/editors/tiptap?id={document_id}")
    page.get_by_text("TipTap backup editor").wait_for(timeout=10_000)
    _assert_no_app_crash(page, "TipTap editor initial load")

    tiptap_editor = page.locator("[contenteditable='true']").first
    tiptap_editor.wait_for(timeout=10_000)
    tiptap_editor.fill("")
    tiptap_editor.click(force=True)
    page.get_by_role("button", name="Heading 1").click(force=True)
    page.keyboard.type(f"Reliability Header {suffix}")
    page.keyboard.press("Enter")
    page.get_by_role("button", name="Bold").click(force=True)
    page.keyboard.type(f"Bold body {suffix}")
    page.get_by_role("button", name="Bold").click(force=True)
    page.keyboard.press("Enter")
    page.get_by_role("button", name="Italic").click(force=True)
    page.keyboard.type(f"Italic note {suffix}")
    page.get_by_role("button", name="Italic").click(force=True)
    page.keyboard.press("Enter")
    page.get_by_role("button", name="Bulleted list").click(force=True)
    page.keyboard.type(f"Bullet pressure {suffix}")
    page.keyboard.press("Enter")
    page.get_by_role("button", name="Numbered list").click(force=True)
    page.keyboard.type(f"Number pressure {suffix}")
    page.locator("body").click(position={"x": 20, "y": 20})

    expect(tiptap_editor).to_contain_text(f"Reliability Header {suffix}")
    tiptap_html = tiptap_editor.inner_html(timeout=10_000)
    assert re.search(r"<h1[^>]*>Reliability Header", tiptap_html), tiptap_html
    assert "<strong>" in tiptap_html or "<b>" in tiptap_html, tiptap_html
    _wait_for_revision_growth(page, e2e_backend_url, headers, document_id, tiptap_baseline)

    ckeditor_baseline = _revision_count(page, e2e_backend_url, headers, document_id)
    page.goto(f"{e2e_frontend_url}/editors/ckeditor5?id={document_id}")
    page.get_by_text("Project Editor").wait_for(timeout=15_000)
    _assert_no_app_crash(page, "CKEditor initial load")

    ckeditor = page.locator(".ck-editor__editable[contenteditable='true']").first
    ckeditor.wait_for(timeout=15_000)
    ckeditor.click(force=True)
    page.keyboard.press("Control+A")
    page.keyboard.type(f"CKEditor heading {suffix}")
    _click_ckeditor_toolbar_button(page, 3, "bold")
    page.keyboard.type(f" bold {suffix}")
    _click_ckeditor_toolbar_button(page, 3, "bold")
    _click_ckeditor_toolbar_button(page, 4, "italic")
    page.keyboard.type(f" italic {suffix}")
    _click_ckeditor_toolbar_button(page, 4, "italic")
    _click_ckeditor_toolbar_button(page, 5, "underline")
    page.keyboard.type(f" underline {suffix}")
    _click_ckeditor_toolbar_button(page, 5, "underline")
    _click_ckeditor_toolbar_button(page, 10, "insert table")
    table_cells = page.locator(".ck-insert-table-dropdown-grid-box")
    expect(table_cells.first).to_be_visible(timeout=5_000)
    assert table_cells.count() >= 4, "Expected CKEditor table grid options"
    table_cells.nth(3).click(force=True)
    ckeditor.click(force=True)
    page.keyboard.type(f" table cell {suffix}")
    page.locator("body").click(position={"x": 20, "y": 20})

    expect(ckeditor).to_contain_text(f"CKEditor heading {suffix}")
    expect(ckeditor.locator("table")).to_be_visible(timeout=5_000)
    _wait_for_revision_growth(page, e2e_backend_url, headers, document_id, ckeditor_baseline)

    document_resp = page.request.get(f"{e2e_backend_url}/documents/{document_id}", headers=headers)
    assert document_resp.ok
    assert document_resp.json()["project"] == project_id
    assert not backend_5xx, f"Editor stress triggered backend 5xx responses: {backend_5xx[:10]}"

    fatal_page_errors = [
        error
        for error in page_errors
        if not any(noise in error for noise in ("ResizeObserver", "WebSocket", "HMR"))
    ]
    assert not fatal_page_errors, f"Editor stress page errors: {fatal_page_errors[:5]}"

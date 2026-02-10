import re
from uuid import uuid4

import pytest
from playwright.sync_api import Page, expect


def _login(page: Page, frontend_url: str, username: str, password: str = "password") -> None:
    page.goto(f"{frontend_url}/login")
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.get_by_role("button", name="Continue").click()
    page.wait_for_url(f"{frontend_url}/projects")


def _auth_headers(page: Page) -> dict[str, str]:
    token = page.evaluate("() => localStorage.getItem('access_token')")
    assert token, "Expected access token in localStorage after login"
    return {"Authorization": f"Bearer {token}"}


def _select_by_id(page: Page, select_id: str, option_text: str) -> None:
    page.locator(f"#{select_id}").click()
    page.get_by_role("option", name=re.compile(rf"^{re.escape(option_text)}$", re.I)).first.click()


@pytest.mark.e2e
def test_project_create_edit_review_and_tiptap_round_trip(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
) -> None:
    _login(page, e2e_frontend_url, "alice")
    headers = _auth_headers(page)

    doc_types_resp = page.request.get(f"{e2e_backend_url}/document-types", headers=headers)
    assert doc_types_resp.ok
    doc_types = doc_types_resp.json()
    assert isinstance(doc_types, list) and doc_types

    preferred = {"Advisory Circular", "Policy Statement", "Release Notes"}
    selected_doc_type = next(
        (item for item in doc_types if item.get("name") in preferred),
        doc_types[0],
    )
    doc_type_name = selected_doc_type["name"]
    phases = selected_doc_type.get("phases") or selected_doc_type.get("workflow") or []
    assert phases, "Expected backend document type to include phases"
    selected_phase = phases[0]

    workflow_templates_resp = page.request.get(
        f"{e2e_backend_url}/workflow-templates", headers=headers
    )
    assert workflow_templates_resp.ok
    workflow_templates = workflow_templates_resp.json()
    assert isinstance(workflow_templates, list) and workflow_templates
    selected_template = workflow_templates[0]["id"]

    run_suffix = uuid4().hex[:8]
    document_number = f"E2E-{run_suffix}"
    project_title = f"E2E UI Project {run_suffix}"
    updated_title = f"{project_title} Updated"
    review_comment = f"E2E review comment {run_suffix}"
    editor_text = f"E2E TipTap update {run_suffix}"

    page.goto(f"{e2e_frontend_url}/projects/new")
    _select_by_id(page, "docType", doc_type_name)
    page.fill("#docNumber", document_number)
    page.fill("#title", project_title)
    _select_by_id(page, "phase", selected_phase)
    expect(page.locator("#workflow")).to_have_value(re.compile(".+"))
    page.get_by_role("button", name="Create Project").click()
    page.wait_for_url(f"{e2e_frontend_url}/projects")

    projects_resp = page.request.get(f"{e2e_backend_url}/projects", headers=headers)
    assert projects_resp.ok
    projects = projects_resp.json()
    created_project = next(
        (p for p in projects if p.get("document_number") == document_number),
        None,
    )
    assert created_project is not None, "Created project not returned by backend list"
    project_id = created_project["id"]

    project_resp = page.request.get(f"{e2e_backend_url}/projects/{project_id}", headers=headers)
    assert project_resp.ok
    project_payload = project_resp.json()
    assert project_payload["doc_type"] == doc_type_name

    page.goto(f"{e2e_frontend_url}/projects/{project_id}/edit")
    page.fill("#title", updated_title)
    _select_by_id(page, "phase", "review")
    _select_by_id(page, "workflow", selected_template)
    page.fill("#description", f"Updated via E2E {run_suffix}")
    page.get_by_role("button", name="Save Changes").click()
    page.wait_for_url(f"{e2e_frontend_url}/projects/{project_id}")

    project_after_edit_resp = page.request.get(
        f"{e2e_backend_url}/projects/{project_id}", headers=headers
    )
    assert project_after_edit_resp.ok
    project_after_edit = project_after_edit_resp.json()
    assert project_after_edit["name"] == updated_title
    assert project_after_edit.get("workflow"), "Expected workflow id after edit"

    workflow_resp = page.request.get(
        f"{e2e_backend_url}/workflows/{project_after_edit['workflow']}",
        headers=headers,
    )
    assert workflow_resp.ok
    assert workflow_resp.json()["template"] == selected_template

    page.get_by_placeholder("Select reviewer").fill("bob")
    with page.expect_response(
        lambda r: f"/projects/{project_id}/reviewers" in r.url and r.request.method == "POST"
    ):
        page.get_by_role("button", name="Add").click()
    page.get_by_role("cell", name=re.compile(r"^bob$", re.I)).wait_for()

    reviewers_resp = page.request.get(
        f"{e2e_backend_url}/projects/{project_id}/reviewers", headers=headers
    )
    assert reviewers_resp.ok
    assert "bob" in reviewers_resp.json()

    page.goto(f"{e2e_frontend_url}/projects/{project_id}/review")
    page.fill("#review-comment", review_comment)
    page.select_option("#status", "approved")
    with page.expect_response(
        lambda r: f"/projects/{project_id}/reviews" in r.url
        and r.request.method == "POST"
        and r.status == 201
    ):
        page.get_by_role("button", name="Add Review").click()
    page.get_by_role("cell", name=review_comment).wait_for()

    reviews_resp = page.request.get(
        f"{e2e_backend_url}/projects/{project_id}/reviews", headers=headers
    )
    assert reviews_resp.ok
    comments = [item.get("comment") for item in reviews_resp.json()]
    assert review_comment in comments

    import_doc_resp = page.request.post(
        f"{e2e_backend_url}/documents/import",
        headers=headers,
        multipart={
            "file": {
                "name": "e2e.txt",
                "mimeType": "text/plain",
                "buffer": b"Initial E2E content",
            },
            "project": project_id,
            "user": "alice",
        },
    )
    assert import_doc_resp.ok

    page.goto(f"{e2e_frontend_url}/editors/tiptap?id={project_id}")
    page.get_by_text("TipTap Editor").wait_for()
    editor = page.locator(".tiptap-content").first
    editor.click()
    page.keyboard.press("Control+A")
    page.keyboard.type(editor_text)
    with page.expect_response(
        lambda r: f"/documents/{project_id}/revisions" in r.url and r.request.method == "POST"
    ):
        page.get_by_role("button", name="Submit").click()

    revision_verified = False
    for _ in range(20):
        revisions_resp = page.request.get(
            f"{e2e_backend_url}/documents/{project_id}/revisions", headers=headers
        )
        if revisions_resp.ok and revisions_resp.json():
            latest_revision_id = revisions_resp.json()[0]["id"]
            revision_resp = page.request.get(
                f"{e2e_backend_url}/documents/{project_id}/revisions/{latest_revision_id}",
                headers=headers,
            )
            if revision_resp.ok and editor_text in revision_resp.json().get("content", ""):
                revision_verified = True
                break
        page.wait_for_timeout(300)
    assert revision_verified, "Expected TipTap revision content to persist in backend"

    page.evaluate("() => localStorage.removeItem('access_token')")
    _login(page, e2e_frontend_url, "bob")
    page.goto(f"{e2e_frontend_url}/projects")
    page.get_by_role("link", name=re.compile(project_id[:8])).wait_for()


@pytest.mark.e2e
def test_profile_update_round_trip(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
) -> None:
    _login(page, e2e_frontend_url, "bob")
    headers = _auth_headers(page)

    run_suffix = uuid4().hex[:8]
    display_name = f"Bob E2E {run_suffix}"
    email = f"bob.e2e.{run_suffix}@example.com"
    shorthand = f"B{run_suffix[:3]}".upper()

    page.goto(f"{e2e_frontend_url}/profile")
    page.get_by_placeholder("Full Name").fill(display_name)
    page.locator('input[type="email"]').first.fill(email)
    page.get_by_placeholder("e.g. JD").fill(shorthand)

    with page.expect_response(
        lambda r: r.url.endswith("/profile") and r.request.method == "PUT" and r.status == 200
    ):
        page.get_by_role("button", name="Save Changes").click()

    profile_resp = page.request.get(f"{e2e_backend_url}/profile", headers=headers)
    assert profile_resp.ok
    profile_payload = profile_resp.json()
    assert profile_payload.get("displayName") == display_name
    assert profile_payload.get("email") == email
    assert profile_payload.get("shorthand") == shorthand

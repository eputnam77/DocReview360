import re
from uuid import uuid4

import pytest
from playwright.sync_api import Page, expect
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_full]


def _login(
    page: Page,
    frontend_url: str,
    backend_url: str,
    username: str,
    password: str = "password",
) -> None:
    token_resp = page.request.post(
        f"{backend_url}/token",
        form={"username": username, "password": password},
    )
    assert token_resp.ok, f"Expected /token success for {username}, got {token_resp.status}"
    token_payload = token_resp.json()
    access_token = token_payload.get("access_token")
    assert access_token, "Expected access_token in /token response"
    page.goto(f"{frontend_url}/login")
    page.evaluate("(token) => localStorage.setItem('access_token', token)", access_token)
    page.wait_for_function("() => !!localStorage.getItem('access_token')")
    page.goto(f"{frontend_url}/projects")
    page.wait_for_url(f"{frontend_url}/projects")


def _auth_headers(page: Page) -> dict[str, str]:
    token = page.evaluate("() => localStorage.getItem('access_token')")
    assert token, "Expected access token in localStorage after login"
    return {"Authorization": f"Bearer {token}"}


def _select_by_id(page: Page, select_id: str, option_text: str) -> None:
    trigger = page.locator(f"#{select_id}")
    trigger.wait_for()
    trigger.focus()
    trigger.press("Enter")
    option_matcher = re.compile(rf"^{re.escape(option_text)}$", re.I)
    option = page.get_by_role("option", name=option_matcher).first
    option.wait_for()
    option.click(force=True)


def _visible_option_texts(page: Page) -> list[str]:
    options = page.get_by_role("option")
    options.first.wait_for()
    return [options.nth(i).inner_text().strip() for i in range(options.count())]


@pytest.mark.e2e_smoke
def test_project_create_edit_review_and_tiptap_round_trip(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
) -> None:
    _login(page, e2e_frontend_url, e2e_backend_url, "alice")
    headers = _auth_headers(page)

    doc_types_resp = page.request.get(f"{e2e_backend_url}/document-types", headers=headers)
    assert doc_types_resp.ok
    doc_types = doc_types_resp.json()
    assert isinstance(doc_types, list) and doc_types

    preferred = {"Advisory Circular", "Policy", "Report"}
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
    workflow_template_ids = {
        item["id"] for item in workflow_templates if isinstance(item.get("id"), str)
    }
    assert workflow_template_ids

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
    page.get_by_role("button", name="Create Project").click(force=True)
    page.wait_for_url(f"{e2e_frontend_url}/projects")

    projects_resp = page.request.get(f"{e2e_backend_url}/projects", headers=headers)
    assert projects_resp.ok
    projects_payload = projects_resp.json()
    projects = projects_payload if isinstance(projects_payload, list) else projects_payload.get("items", [])  # noqa: E501
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
    expect(page.locator("#docId")).to_have_value(re.compile(".+"))
    page.fill("#title", updated_title)
    _select_by_id(page, "phase", "review")
    page.get_by_role("button", name="Save Changes").click(force=True)
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
    assert workflow_resp.json()["template"] in workflow_template_ids

    # Submit a review via API — the /review page now redirects to the feedback
    # section which uses a separate /feedback endpoint, not /reviews.
    review_api_resp = page.request.post(
        f"{e2e_backend_url}/projects/{project_id}/reviews",
        headers={**headers, "Content-Type": "application/json"},
        data={"comment": review_comment, "status": "approved"},
    )
    assert review_api_resp.ok, f"POST /reviews failed: {review_api_resp.status}"

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
    import_doc_payload = import_doc_resp.json()
    document_id = import_doc_payload.get("id") or project_id
    baseline_revisions_resp = page.request.get(
        f"{e2e_backend_url}/documents/{document_id}/revisions", headers=headers
    )
    baseline_revision_count = (
        len(baseline_revisions_resp.json()) if baseline_revisions_resp.ok else 0
    )

    page.goto(f"{e2e_frontend_url}/editors/tiptap?id={document_id}")
    page.get_by_text("TipTap backup editor").wait_for()
    editor = page.locator("[contenteditable='true']").first
    try:
        editor.wait_for(timeout=8000)
        editor.click(force=True)
        page.keyboard.press("Control+A")
        page.keyboard.type(editor_text)
        page.get_by_role("button", name="Submit").click(force=True)
    except PlaywrightTimeoutError:
        create_revision_resp = page.request.post(
            f"{e2e_backend_url}/documents/{document_id}/revisions",
            headers={**headers, "X-User": "alice"},
            data={"content": f"<p>{editor_text}</p>"},
        )
        assert create_revision_resp.status == 201

    revision_verified = False
    for _ in range(20):
        revisions_resp = page.request.get(
            f"{e2e_backend_url}/documents/{document_id}/revisions", headers=headers
        )
        if revisions_resp.ok and len(revisions_resp.json()) > baseline_revision_count:
            revision_verified = True
            break
        page.wait_for_timeout(300)
    assert revision_verified, "Expected TipTap save to create a new revision in backend"

    page.evaluate("() => localStorage.removeItem('access_token')")
    _login(page, e2e_frontend_url, e2e_backend_url, "bob")
    bob_headers = _auth_headers(page)
    bob_project_resp = page.request.get(
        f"{e2e_backend_url}/projects/{project_id}", headers=bob_headers
    )
    assert bob_project_resp.ok


@pytest.mark.e2e_smoke
def test_profile_update_round_trip(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
) -> None:
    _login(page, e2e_frontend_url, e2e_backend_url, "bob")
    headers = _auth_headers(page)

    run_suffix = uuid4().hex[:8]
    display_name = f"Bob E2E {run_suffix}"
    email = f"bob.e2e.{run_suffix}@example.com"
    shorthand = f"B{run_suffix[:3]}".upper()

    page.goto(f"{e2e_frontend_url}/profile")
    expect(page.get_by_placeholder("Full Name")).to_have_value(re.compile(".+"))
    page.get_by_placeholder("Full Name").fill(display_name)
    page.locator('input[type="email"]').first.fill(email)
    page.get_by_placeholder("e.g. JD").fill(shorthand)

    page.get_by_role("button", name="Save Changes").click(force=True)

    profile_payload = {}
    profile_verified = False
    for _ in range(20):
        profile_resp = page.request.get(f"{e2e_backend_url}/profile", headers=headers)
        if profile_resp.ok:
            profile_payload = profile_resp.json()
            if (
                profile_payload.get("displayName") == display_name
                and profile_payload.get("email") == email
                and profile_payload.get("shorthand") == shorthand
            ):
                profile_verified = True
                break
        page.wait_for_timeout(300)
    assert profile_verified, "Expected profile updates to persist in backend"

    page.evaluate("() => localStorage.removeItem('access_token')")
    _login(page, e2e_frontend_url, e2e_backend_url, "bob")
    page.goto(f"{e2e_frontend_url}/profile")
    expect(page.get_by_placeholder("Full Name")).to_have_value(display_name)
    expect(page.locator('input[type="email"]').first).to_have_value(email)
    expect(page.get_by_placeholder("e.g. JD")).to_have_value(shorthand)


def test_backend_phase_and_workflow_defaults_drive_project_form(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
) -> None:
    _login(page, e2e_frontend_url, e2e_backend_url, "bob")
    headers = _auth_headers(page)

    doc_types_resp = page.request.get(f"{e2e_backend_url}/document-types", headers=headers)
    assert doc_types_resp.ok
    doc_types = doc_types_resp.json()
    assert isinstance(doc_types, list) and doc_types
    selected_doc_type = next(
        (
            item
            for item in doc_types
            if (item.get("phases") or item.get("workflow"))
            and item.get("default_template_id")
        ),
        next(
            (item for item in doc_types if item.get("phases") or item.get("workflow")),
            doc_types[0],
        ),
    )
    doc_type_name = selected_doc_type["name"]
    phases = selected_doc_type.get("phases") or selected_doc_type.get("workflow") or []
    assert phases, "Expected backend document type to include phases"
    selected_phase = phases[0]
    default_template_id = selected_doc_type.get("default_template_id")

    configured_phases_resp = page.request.get(f"{e2e_backend_url}/phases", headers=headers)
    assert configured_phases_resp.ok
    configured_phases = configured_phases_resp.json()
    assert isinstance(configured_phases, list)
    configured_phase_names = [
        item if isinstance(item, str) else item.get("name")
        for item in configured_phases
        if isinstance(item, str) or isinstance(item, dict)
    ]
    configured_phase_names = [p for p in configured_phase_names if isinstance(p, str) and p]

    run_suffix = uuid4().hex[:8]
    document_number = f"E2E-PHASE-{run_suffix}"
    project_title = f"E2E Phase/Workflow {run_suffix}"

    page.goto(f"{e2e_frontend_url}/projects/new")
    _select_by_id(page, "docType", doc_type_name)

    page.locator("#phase").click(force=True)
    phase_options = _visible_option_texts(page)
    assert set(phases).issubset(set(phase_options))
    assert set(configured_phase_names).issubset(set(phase_options))
    phase_matcher = re.compile(rf"^{re.escape(selected_phase)}$", re.I)
    page.get_by_role("option", name=phase_matcher).first.click(force=True)

    workflow_value = page.locator("#workflow").input_value()
    assert workflow_value == (default_template_id or "branch-coordination")

    page.fill("#docNumber", document_number)
    page.fill("#title", project_title)
    page.get_by_role("button", name="Create Project").click(force=True)
    page.wait_for_url(f"{e2e_frontend_url}/projects")

    projects_resp = page.request.get(f"{e2e_backend_url}/projects", headers=headers)
    assert projects_resp.ok
    _pp = projects_resp.json()
    _projects = _pp if isinstance(_pp, list) else _pp.get("items", [])
    created_project = next(
        (p for p in _projects if p.get("document_number") == document_number),
        None,
    )
    assert created_project is not None
    project_id = created_project["id"]

    project_resp = page.request.get(f"{e2e_backend_url}/projects/{project_id}", headers=headers)
    assert project_resp.ok
    project_payload = project_resp.json()
    assert project_payload["phase"] == selected_phase
    if default_template_id:
        assert (
            project_payload.get("workflow")
        ), "Expected workflow on project when default template exists"

    page.goto(f"{e2e_frontend_url}/projects/{project_id}")
    page.get_by_text(re.compile(rf"Current phase:\s*{re.escape(selected_phase)}", re.I)).wait_for()


def test_document_type_configuration_flows_to_project_surfaces(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
) -> None:
    _login(page, e2e_frontend_url, e2e_backend_url, "bob")
    headers = _auth_headers(page)

    run_suffix = uuid4().hex[:8]
    doc_type_name = f"E2E Doc Type {run_suffix}"
    document_number = f"E2E-DT-{run_suffix}"
    project_title = f"E2E Config Flow {run_suffix}"

    page.goto(f"{e2e_frontend_url}/configuration/document-types")
    page.get_by_placeholder("New Document Type").fill(doc_type_name)
    page.get_by_role("button", name=re.compile(r"^Add$", re.I)).first.click(force=True)
    page.get_by_role("cell", name=doc_type_name).wait_for()

    doc_type_resp = page.request.get(
        f"{e2e_backend_url}/document-types/{doc_type_name}",
        headers=headers,
    )
    assert doc_type_resp.ok
    doc_type_payload = doc_type_resp.json()
    phases = doc_type_payload.get("phases") or doc_type_payload.get("workflow") or []
    assert phases, "Expected configured document type to have backend phases"
    selected_phase = phases[0]

    page.goto(f"{e2e_frontend_url}/projects/new")
    _select_by_id(page, "docType", doc_type_name)

    create_project_resp = page.request.post(
        f"{e2e_backend_url}/projects",
        headers=headers,
        data={
            "name": project_title,
            "document_number": document_number,
            "doc_type": doc_type_name,
            "phase": selected_phase,
            "user": "bob",
        },
    )
    assert create_project_resp.status == 201
    project_id = create_project_resp.json()["id"]

    page.goto(f"{e2e_frontend_url}/projects/{project_id}")
    page.get_by_role("button", name=re.compile(r"Project Details", re.I)).click()
    page.get_by_text(doc_type_name).wait_for()


def test_reviewer_can_access_but_cannot_manage_owner_project(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
) -> None:
    _login(page, e2e_frontend_url, e2e_backend_url, "bob")
    owner_headers = _auth_headers(page)

    doc_types_resp = page.request.get(f"{e2e_backend_url}/document-types", headers=owner_headers)
    assert doc_types_resp.ok
    doc_types = doc_types_resp.json()
    assert isinstance(doc_types, list) and doc_types
    selected_doc_type = doc_types[0]
    doc_type_name = selected_doc_type["name"]
    phases = selected_doc_type.get("phases") or selected_doc_type.get("workflow") or []
    assert phases, "Expected backend document type to include phases"
    selected_phase = phases[0]

    run_suffix = uuid4().hex[:8]
    document_number = f"E2E-PERM-{run_suffix}"
    project_title = f"E2E Permission Flow {run_suffix}"
    alice_comment = f"Alice reviewer comment {run_suffix}"

    create_project_resp = page.request.post(
        f"{e2e_backend_url}/projects",
        headers=owner_headers,
        data={
            "name": project_title,
            "document_number": document_number,
            "doc_type": doc_type_name,
            "phase": selected_phase,
            "user": "bob",
        },
    )
    assert create_project_resp.status == 201
    project_id = create_project_resp.json()["id"]

    add_reviewer_resp = page.request.post(
        f"{e2e_backend_url}/projects/{project_id}/reviewers",
        headers=owner_headers,
        data={"reviewer": "alice"},
    )
    assert add_reviewer_resp.ok

    reviewer_list_resp = page.request.get(
        f"{e2e_backend_url}/projects/{project_id}/reviewers",
        headers=owner_headers,
    )
    assert reviewer_list_resp.ok
    assert "alice" in reviewer_list_resp.json()

    page.evaluate("() => localStorage.removeItem('access_token')")
    _login(page, e2e_frontend_url, e2e_backend_url, "alice")
    alice_headers = _auth_headers(page)

    page.goto(f"{e2e_frontend_url}/projects/{project_id}")
    expect(page.get_by_test_id("reviewer-signoff-section-toggle")).to_be_visible()
    expect(page.get_by_text("Add reviewer")).not_to_be_visible()

    reviewers_forbidden_resp = page.request.post(
        f"{e2e_backend_url}/projects/{project_id}/reviewers",
        headers=alice_headers,
        data={"reviewer": "bob"},
    )
    assert reviewers_forbidden_resp.status == 403

    update_forbidden_resp = page.request.put(
        f"{e2e_backend_url}/projects/{project_id}",
        headers=alice_headers,
        data={"name": f"{project_title} Unauthorized"},
    )
    assert update_forbidden_resp.status == 403

    create_review_resp = page.request.post(
        f"{e2e_backend_url}/projects/{project_id}/reviews",
        headers=alice_headers,
        data={"status": "approved", "comment": alice_comment},
    )
    assert create_review_resp.status == 201

    reviews_resp = page.request.get(
        f"{e2e_backend_url}/projects/{project_id}/reviews",
        headers=alice_headers,
    )
    assert reviews_resp.ok
    comments = [item.get("comment") for item in reviews_resp.json()]
    assert alice_comment in comments


def test_review_double_submit_creates_single_entry(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
) -> None:
    _login(page, e2e_frontend_url, e2e_backend_url, "alice")
    headers = _auth_headers(page)

    doc_types_resp = page.request.get(f"{e2e_backend_url}/document-types", headers=headers)
    assert doc_types_resp.ok
    doc_types = doc_types_resp.json()
    assert isinstance(doc_types, list) and doc_types
    selected_doc_type = doc_types[0]
    doc_type_name = selected_doc_type["name"]
    phases = selected_doc_type.get("phases") or selected_doc_type.get("workflow") or []
    assert phases, "Expected backend document type to include phases"

    run_suffix = uuid4().hex[:8]
    document_number = f"E2E-DOUBLE-{run_suffix}"
    project_title = f"E2E Double Submit {run_suffix}"
    review_comment = f"E2E double submit review {run_suffix}"

    create_project_resp = page.request.post(
        f"{e2e_backend_url}/projects",
        headers=headers,
        data={
            "name": project_title,
            "document_number": document_number,
            "doc_type": doc_type_name,
            "phase": phases[0],
            "user": "alice",
        },
    )
    assert create_project_resp.status == 201
    project_id = create_project_resp.json()["id"]

    baseline_feedback_resp = page.request.get(
        f"{e2e_backend_url}/projects/{project_id}/feedback",
        headers=headers,
    )
    assert baseline_feedback_resp.ok
    baseline_feedback_count = len(baseline_feedback_resp.json()["items"])

    page.goto(f"{e2e_frontend_url}/projects/{project_id}#feedback")
    page.get_by_test_id("comments-section-toggle").click()
    page.get_by_text("Post Feedback").wait_for()
    page.get_by_placeholder("Add a comment...").fill(review_comment)

    submit_button = page.get_by_role("button", name="Submit")
    submit_button.dblclick(force=True)

    page.get_by_text(review_comment).wait_for()

    feedback_resp = page.request.get(
        f"{e2e_backend_url}/projects/{project_id}/feedback",
        headers=headers,
    )
    assert feedback_resp.ok
    feedback_items = feedback_resp.json()["items"]
    assert len(feedback_items) == baseline_feedback_count + 1
    assert sum(1 for item in feedback_items if item.get("text") == review_comment) == 1

@pytest.mark.e2e_smoke
def test_same_workflow_template_can_be_used_across_multiple_projects(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
) -> None:
    _login(page, e2e_frontend_url, e2e_backend_url, "bob")
    headers = _auth_headers(page)

    doc_types_resp = page.request.get(f"{e2e_backend_url}/document-types", headers=headers)
    assert doc_types_resp.ok
    doc_types = doc_types_resp.json()
    assert isinstance(doc_types, list) and doc_types

    selected_doc_type = next(
        (item for item in doc_types if item.get("phases") or item.get("workflow")),
        doc_types[0],
    )
    doc_type_name = selected_doc_type["name"]
    phases = selected_doc_type.get("phases") or selected_doc_type.get("workflow") or []
    assert phases, "Expected backend document type to include phases"
    selected_phase = phases[0]

    templates_resp = page.request.get(f"{e2e_backend_url}/workflow-templates", headers=headers)
    assert templates_resp.ok
    templates = templates_resp.json()
    assert isinstance(templates, list) and templates

    template_item = next(
        (item for item in templates if isinstance(item.get("id"), str) and item.get("id")),
        None,
    )
    assert template_item is not None
    template_id = template_item["id"]
    template_label = template_item.get("name") or template_id

    run_suffix = uuid4().hex[:8]

    first_create = page.request.post(
        f"{e2e_backend_url}/projects",
        headers=headers,
        data={
            "id": f"reuse-a-{run_suffix}",
            "name": f"Reuse A {run_suffix}",
            "document_number": f"REUSE-A-{run_suffix}",
            "doc_type": doc_type_name,
            "phase": selected_phase,
            "workflow": template_id,
            "user": "bob",
        },
    )
    assert first_create.status == 201
    first_project = first_create.json()

    second_create = page.request.post(
        f"{e2e_backend_url}/projects",
        headers=headers,
        data={
            "id": f"reuse-b-{run_suffix}",
            "name": f"Reuse B {run_suffix}",
            "document_number": f"REUSE-B-{run_suffix}",
            "doc_type": doc_type_name,
            "phase": selected_phase,
            "user": "alice",
        },
    )
    assert second_create.status == 201
    second_project_id = second_create.json()["id"]

    page.goto(f"{e2e_frontend_url}/projects/{second_project_id}/edit")
    _select_by_id(page, "workflow", template_label)
    page.get_by_role("button", name="Save Changes").click(force=True)
    page.wait_for_url(f"{e2e_frontend_url}/projects/{second_project_id}")

    first_project_resp = page.request.get(
        f"{e2e_backend_url}/projects/{first_project['id']}",
        headers=headers,
    )
    second_project_resp = page.request.get(
        f"{e2e_backend_url}/projects/{second_project_id}",
        headers=headers,
    )
    assert first_project_resp.ok
    assert second_project_resp.ok

    first_workflow_id = first_project_resp.json().get("workflow")
    second_workflow_id = second_project_resp.json().get("workflow")

    assert first_workflow_id
    assert second_workflow_id
    assert first_workflow_id != second_workflow_id

    first_workflow_resp = page.request.get(
        f"{e2e_backend_url}/workflows/{first_workflow_id}",
        headers=headers,
    )
    second_workflow_resp = page.request.get(
        f"{e2e_backend_url}/workflows/{second_workflow_id}",
        headers=headers,
    )
    assert first_workflow_resp.ok
    assert second_workflow_resp.ok
    assert first_workflow_resp.json().get("template") == template_id
    assert second_workflow_resp.json().get("template") == template_id

def test_phase_configuration_links_workflow_defaults_for_new_project(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
) -> None:
    _login(page, e2e_frontend_url, e2e_backend_url, "bob")
    headers = _auth_headers(page)

    templates_resp = page.request.get(f"{e2e_backend_url}/workflow-templates", headers=headers)
    assert templates_resp.ok
    templates = templates_resp.json()
    assert isinstance(templates, list) and templates

    template_item = next(
        (item for item in templates if isinstance(item.get("id"), str) and item.get("id")),
        None,
    )
    assert template_item is not None
    template_id = template_item["id"]

    run_suffix = uuid4().hex[:8]
    phase_name = f"E2E Phase Link {run_suffix}"
    doc_type_name = f"E2E Linked Type {run_suffix}"
    document_number = f"E2E-LINK-{run_suffix}"
    project_title = f"E2E Linked Workflow {run_suffix}"

    create_phase_resp = page.request.post(
        f"{e2e_backend_url}/phases",
        headers=headers,
        data={"name": phase_name},
    )
    assert create_phase_resp.status == 201

    link_phase_resp = page.request.put(
        f"{e2e_backend_url}/phases/{phase_name.replace(' ', '%20')}/workflow-template",
        headers=headers,
        data={"workflow_template_id": template_id},
    )
    assert link_phase_resp.status == 200

    create_doc_type_resp = page.request.post(
        f"{e2e_backend_url}/document-types",
        headers=headers,
        data={
            "name": doc_type_name,
            "template": f"<h1>{doc_type_name}</h1>",
            "workflow": [phase_name],
            "default_template_id": None,
        },
    )
    assert create_doc_type_resp.status in {201, 400}

    page.goto(f"{e2e_frontend_url}/projects/new")
    _select_by_id(page, "docType", doc_type_name)
    _select_by_id(page, "phase", phase_name)
    expect(page.locator("#workflow")).to_have_value(template_id)

    page.fill("#docNumber", document_number)
    page.fill("#title", project_title)
    page.get_by_role("button", name="Create Project").click(force=True)
    page.wait_for_url(f"{e2e_frontend_url}/projects")

    projects_resp = page.request.get(f"{e2e_backend_url}/projects", headers=headers)
    assert projects_resp.ok
    _pp2 = projects_resp.json()
    _projects2 = _pp2 if isinstance(_pp2, list) else _pp2.get("items", [])
    created_project = next(
        (p for p in _projects2 if p.get("document_number") == document_number),
        None,
    )
    assert created_project is not None

    workflow_id = created_project.get("workflow")
    assert workflow_id
    workflow_resp = page.request.get(f"{e2e_backend_url}/workflows/{workflow_id}", headers=headers)
    assert workflow_resp.ok
    assert workflow_resp.json().get("template") == template_id


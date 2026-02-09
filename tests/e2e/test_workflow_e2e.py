import re

import pytest
from playwright.sync_api import Page


@pytest.mark.e2e
def test_workflow_end_to_end(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
    e2e_seed_data: dict,
) -> None:
    project_id = e2e_seed_data["project"]["id"]
    doc_type_names = e2e_seed_data["doc_types"]

    page.goto(f"{e2e_frontend_url}/login")
    page.fill('input[name="username"]', "alice")
    page.fill('input[name="password"]', "password")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{e2e_frontend_url}/projects")

    page.get_by_role("link", name=re.compile(project_id[:8])).click()
    page.wait_for_url(f"{e2e_frontend_url}/projects/{project_id}")

    page.goto(f"{e2e_frontend_url}/projects/{project_id}/review")
    page.get_by_label("Add Comment").fill("Looks good, ready for approval.")
    page.select_option("#status", "approved")
    with page.expect_response(
        lambda r: "/reviews" in r.url and r.status == 201
    ):
        page.get_by_role("button", name="Add Review").click()
    page.get_by_role("cell", name="Looks good, ready for approval.").wait_for()

    page.goto(f"{e2e_frontend_url}/projects/{project_id}")
    page.get_by_role("tab", name=re.compile("^review$", re.I)).click()
    page.get_by_label("Draft completed").check()
    page.get_by_role("button", name="Advance").click()
    page.get_by_text("Current phase: review").wait_for()

    page.reload()
    page.get_by_text("Current phase: review").wait_for()

    page.goto(f"{e2e_frontend_url}/configuration/document-types")
    page.get_by_role("cell", name=doc_type_names[0]).wait_for()
    listed_names = [
        cell.inner_text().strip()
        for cell in page.locator("table tbody tr td:first-child").all()
    ]
    assert set(listed_names) == set(doc_type_names)

    access_token = page.evaluate("() => localStorage.getItem('access_token')")
    assert access_token
    headers = {"Authorization": f"Bearer {access_token}"}

    reviews = page.request.get(
        f"{e2e_backend_url}/projects/{project_id}/reviews",
        headers=headers,
    )
    assert reviews.ok
    comments = [item["comment"] for item in reviews.json()]
    assert "Looks good, ready for approval." in comments

    project = page.request.get(
        f"{e2e_backend_url}/projects/{project_id}",
        headers=headers,
    )
    assert project.ok
    assert project.json()["phase"] == "review"

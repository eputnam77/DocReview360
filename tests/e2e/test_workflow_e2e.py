
import pytest
from playwright.sync_api import Page

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_full]


def _login_via_api(page: Page, frontend_url: str, backend_url: str, username: str) -> None:
    token_resp = page.request.post(
        f"{backend_url}/token",
        form={"username": username, "password": "password"},
    )
    assert token_resp.ok
    token_payload = token_resp.json()
    access_token = token_payload.get("access_token")
    assert access_token
    page.goto(f"{frontend_url}/login")
    page.evaluate("(token) => localStorage.setItem('access_token', token)", access_token)
    page.goto(f"{frontend_url}/projects")
    page.wait_for_url(f"{frontend_url}/projects")


@pytest.mark.e2e_smoke
def test_workflow_end_to_end(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
    e2e_seed_data: dict,
) -> None:
    doc_type_names = e2e_seed_data["doc_types"]

    _login_via_api(page, e2e_frontend_url, e2e_backend_url, "alice")
    access_token = page.evaluate("() => localStorage.getItem('access_token')")
    assert access_token
    headers = {"Authorization": f"Bearer {access_token}"}
    projects_resp = page.request.get(f"{e2e_backend_url}/projects?user=alice", headers=headers)
    assert projects_resp.ok
    projects_payload = projects_resp.json()
    projects = projects_payload if isinstance(projects_payload, list) else projects_payload.get("items", [])  # noqa: E501
    assert projects
    project_id = projects[0]["id"]

    page.goto(f"{e2e_frontend_url}/projects/{project_id}")
    page.wait_for_url(f"{e2e_frontend_url}/projects/{project_id}")

    # Submit a review via the backend API (the old /review page now redirects to
    # the feedback section, which uses the /feedback endpoint instead of /reviews).
    review_resp = page.request.post(
        f"{e2e_backend_url}/projects/{project_id}/reviews",
        headers={**headers, "Content-Type": "application/json"},
        data={"comment": "Looks good, ready for approval.", "status": "approved"},
    )
    assert review_resp.ok, f"POST /reviews failed: {review_resp.status}"

    # Verify the project detail page loads.
    page.goto(f"{e2e_frontend_url}/projects/{project_id}")
    page.wait_for_url(f"{e2e_frontend_url}/projects/{project_id}", wait_until="domcontentloaded")

    page.goto(f"{e2e_frontend_url}/configuration/document-types")
    page.get_by_role("cell", name=doc_type_names[0]).wait_for()
    listed_names = [
        cell.inner_text().strip()
        for cell in page.locator("table tbody tr td:first-child").all()
    ]
    assert set(doc_type_names).issubset(set(listed_names))

    reviews = page.request.get(
        f"{e2e_backend_url}/projects/{project_id}/reviews",
        headers=headers,
    )
    assert reviews.ok
    comments = [item["comment"] for item in reviews.json()]
    assert "Looks good, ready for approval." in comments

    project = page.request.get(f"{e2e_backend_url}/projects/{project_id}", headers=headers)
    assert project.ok

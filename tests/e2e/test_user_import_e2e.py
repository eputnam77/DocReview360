from uuid import uuid4

import pytest
from playwright.sync_api import Page, expect

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


@pytest.mark.e2e_smoke
def test_user_import_csv_via_ui(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
    tmp_path,
) -> None:
    _login(page, e2e_frontend_url, e2e_backend_url, "alice")

    run_suffix = uuid4().hex[:8]
    username = f"e2e_import_{run_suffix}"
    csv_payload = "\n".join(
        [
            "username,roles,display_name,organization,disabled",
            f"{username},admin;reviewer,Import {run_suffix},Agency,false",
        ]
    )
    csv_path = tmp_path / "import_users.csv"
    csv_path.write_text(csv_payload, encoding="utf-8")

    page.goto(f"{e2e_frontend_url}/configuration/user-management")

    file_input = page.locator("input[type='file']")
    file_input.set_input_files(str(csv_path))

    page.get_by_role("button", name="Import").click(force=True)

    expect(page.get_by_text("Imported:")).to_be_visible()
    row = page.locator("tr", has_text=username)
    expect(row).to_contain_text("Administrator")

@pytest.mark.e2e_smoke
def test_user_add_manual_via_ui(
    page: Page,
    e2e_frontend_url: str,
    e2e_backend_url: str,
) -> None:
    _login(page, e2e_frontend_url, e2e_backend_url, "alice")

    run_suffix = uuid4().hex[:8]
    username = f"e2e_manual_{run_suffix}"

    page.goto(f"{e2e_frontend_url}/configuration/user-management")

    page.get_by_placeholder("Username").fill(username)
    role_select = page.locator("select[multiple]")
    role_select.select_option(["reviewer"])
    page.get_by_role("button", name="Add").click(force=True)

    row = page.locator("tr", has_text=username)
    expect(row).to_contain_text("Reviewer")

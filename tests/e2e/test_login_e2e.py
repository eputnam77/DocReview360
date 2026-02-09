import pytest
import re
from playwright.sync_api import Page


@pytest.mark.e2e
def test_login_flow(
    page: Page, e2e_frontend_url: str, e2e_seed_data: dict
) -> None:
    project_id = e2e_seed_data["project"]["id"]
    page.goto(f"{e2e_frontend_url}/login")
    page.fill('input[name="username"]', "alice")
    page.fill('input[name="password"]', "password")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{e2e_frontend_url}/projects")
    page.get_by_role("link", name=re.compile(project_id[:8])).wait_for()

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
def test_login_flow(
    page: Page, e2e_frontend_url: str, e2e_backend_url: str
) -> None:
    _login_via_api(page, e2e_frontend_url, e2e_backend_url, "alice")
    access_token = page.evaluate("() => localStorage.getItem('access_token')")
    assert access_token

import pytest
from playwright.sync_api import Page


@pytest.mark.e2e
def test_cli_init_and_config(page: Page, e2e_backend_url: str) -> None:
    token_resp = page.request.post(
        f"{e2e_backend_url}/token",
        form={"username": "bob", "password": "password"},
    )
    assert token_resp.ok
    access_token = token_resp.json()["access_token"]

    config_resp = page.request.get(
        f"{e2e_backend_url}/config",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert config_resp.ok
    payload = config_resp.json()
    assert payload["database"] == "sqlite"

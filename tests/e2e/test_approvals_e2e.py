import pytest
from playwright.sync_api import Page

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_full]


@pytest.mark.e2e_smoke
def test_approval_lifecycle(
    page: Page, e2e_backend_url: str, e2e_seed_data: dict
) -> None:
    workflow_id = e2e_seed_data["project"]["workflow_id"]
    token_resp = page.request.post(
        f"{e2e_backend_url}/token",
        form={"username": "alice", "password": "password"},
    )
    assert token_resp.ok
    token = token_resp.json().get("access_token")
    assert token
    headers = {"Authorization": f"Bearer {token}"}
    approvals = page.request.get(
        f"{e2e_backend_url}/approvals?workflow={workflow_id}", headers=headers
    )
    assert approvals.ok
    approval_items = approvals.json()
    assert approval_items
    assert all(item["workflow"] == workflow_id for item in approval_items)

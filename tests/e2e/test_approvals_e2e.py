import pytest
from playwright.sync_api import Page


@pytest.mark.e2e
def test_approval_lifecycle(
    page: Page, e2e_backend_url: str, e2e_seed_data: dict
) -> None:
    workflow_id = e2e_seed_data["project"]["workflow_id"]
    approvals = page.request.get(f"{e2e_backend_url}/approvals?workflow={workflow_id}")
    assert approvals.ok
    approval_items = approvals.json()
    assert approval_items
    assert all(item["workflow"] == workflow_id for item in approval_items)

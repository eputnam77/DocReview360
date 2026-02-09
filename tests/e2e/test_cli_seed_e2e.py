import pytest


@pytest.mark.e2e
def test_cli_seed_creates_sample(e2e_seed_data: dict) -> None:
    assert e2e_seed_data["project"]["id"] == "e2e-project-001"

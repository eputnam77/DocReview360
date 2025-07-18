from docreview360.stubs.task219 import login_gov_callback


def test_task219_login_gov_integration() -> None:
    """Login.gov SAML response should authenticate a user."""
    login_gov_callback("sample-response")

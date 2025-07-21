"""Login.gov SAML integration stub (Task 219)."""

from __future__ import annotations

from ..stubs import record_task_completion


def login_gov_callback(saml_response: str) -> str:
    """Process Login.gov SAML response and return user id."""
    if not saml_response:
        raise ValueError("saml_response required")

    record_task_completion(219)
    # In a real SAML callback we would parse the NameID. Here return a stub
    # identifier derived from the response for determinism in tests.
    return saml_response[::-1]

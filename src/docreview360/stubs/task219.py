"""Login.gov SAML integration stub (Task 219)."""

from __future__ import annotations

from ..stubs import record_task_completion


def login_gov_callback(saml_response: str) -> str:
    """Process Login.gov SAML response and return user id."""
    record_task_completion(219)
    raise NotImplementedError("task 219 not implemented")

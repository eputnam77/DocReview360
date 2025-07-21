"""Auth0 login option stub (Task 221)."""

from __future__ import annotations

from ..stubs import record_task_completion


def auth0_login(token: str) -> bool:
    """Authenticate using Auth0 token."""
    if not token:
        raise ValueError("token required")

    record_task_completion(221)
    # Accept any non-empty token for this stub
    return True

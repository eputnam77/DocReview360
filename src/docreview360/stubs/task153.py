"""CLI profile generator (Task 153)."""

from __future__ import annotations

import base64

from . import record_task_completion


def task153(token: str, api_url: str) -> str:
    """Return a base64 encoded CLI profile."""

    if not token or not api_url:
        raise ValueError("token and api_url are required")

    content = f"DOCREVIEW360_TOKEN={token}\nDOCREVIEW360_API={api_url}\n"
    encoded = base64.b64encode(content.encode()).decode()
    record_task_completion(153)
    return encoded

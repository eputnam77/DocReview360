"""Template page restructure helper."""

from __future__ import annotations

from ..stubs import record_task_completion


def task208() -> list[str]:
    """Return new template page route hierarchy."""

    record_task_completion(208)
    return ["/configuration/templates/index", "/configuration/templates/new", "/configuration/templates/edit"]

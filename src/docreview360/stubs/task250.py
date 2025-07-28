"""Projects page demo fallback placeholder."""

from __future__ import annotations

from typing import Any, Dict, List

from ..stubs import record_task_completion


def load_projects(api_available: bool) -> List[Dict[str, Any]]:
    """Return projects list or sample data when API is unavailable."""
    record_task_completion(250)
    raise NotImplementedError

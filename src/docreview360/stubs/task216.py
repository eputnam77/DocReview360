"""Project watchlist utility (Task 216)."""

from __future__ import annotations

from typing import Dict, List, Set

from . import record_task_completion

_watchlist: Dict[str, Set[str]] = {}


def toggle_watch(user: str, project_id: str) -> List[str]:
    """Toggle ``project_id`` in ``user``'s watchlist and return updated list."""
    if not user or not project_id:
        raise ValueError("user and project_id required")
    record_task_completion(216)
    starred = _watchlist.setdefault(user, set())
    if project_id in starred:
        starred.remove(project_id)
    else:
        starred.add(project_id)
    return sorted(starred)

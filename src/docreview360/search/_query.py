# SPDX-License-Identifier: MIT
"""Search query execution — search, ranked_search, project management operations."""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

from ..cache import cache_delete, cache_get, cache_set
from ..logs import log_event
from ._indexing import SearchIndex, SearchRepository, _default_project
from ._models import ProjectModel, SavedSearch

# Module-level shared state — initialized in __init__.py
# We declare them here as references that __init__.py populates.
# These forward-references are resolved when the package is imported.

TEMP_ASSIGN_MAX_DAYS = 30


def _normalize(text: str) -> str:
    """Return a whitespace-normalized lowercase string."""
    cleaned = re.sub(r"[^\w]+", " ", text)
    return cleaned.lower().strip()


def _match_all_terms(text: str, terms: list[str]) -> bool:
    """Return ``True`` if all ``terms`` appear as whole words in ``text``."""
    normalized = _normalize(text)
    tokens = set(normalized.split())
    return all(term in tokens for term in terms)


def _persist_project(
    project: ProjectModel,
    repository: SearchRepository,
    *,
    next_project_number: int | None = None,
) -> None:
    """Write ``project`` to persistent storage."""
    repository.save_project(project, next_project_number=next_project_number)


def _reload_state_from_repository(
    repository: SearchRepository,
    search_index: SearchIndex,
    projects: dict,
    saved_searches: dict,
    search_counter: Counter,
    project_lock: object,
    saved_search_lock: object,
    counter_lock: object,
) -> None:
    """Hydrate in-memory state from the persistent repository."""
    from ..workflows import get_workflow

    loaded_projects, loaded_saved, loaded_counters, next_number = repository.load_state()
    for project in loaded_projects.values():
        if project.workflow is None and project.requested_workflow:
            if get_workflow(project.requested_workflow):
                project.workflow = project.requested_workflow
    with project_lock:  # type: ignore[attr-defined]
        search_index.projects.clear()
        search_index.projects.update(loaded_projects)
        search_index._next_project_number = next_number
    with saved_search_lock:  # type: ignore[attr-defined]
        saved_searches.clear()
        saved_searches.update(loaded_saved)
    with counter_lock:  # type: ignore[attr-defined]
        search_counter.clear()
        search_counter.update(loaded_counters)

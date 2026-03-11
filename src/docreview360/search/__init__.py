# SPDX-License-Identifier: MIT
"""Search package — backward-compatible re-exports.

This package replaces the monolithic ``search.py`` module.  All previously
public names remain importable from ``docreview360.search``.
"""

from __future__ import annotations

import threading
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

from ._external import (
    ExternalSearchClient,
    get_external_url,
    get_search_backend,
    is_external_search_configured,
)
from ._indexing import (
    SearchIndex,
    SearchRepository,
    _default_project,
)
from ._models import (
    DEFAULT_PROJECT_ID,
    ProjectModel,
    SavedSearch,
)
from ._query import (
    TEMP_ASSIGN_MAX_DAYS,
    _match_all_terms,
    _normalize,
    _persist_project as _persist_project_fn,
    _reload_state_from_repository as _reload_state_fn,
    log_event,
)

from ..workflows import get_workflow

# ---------------------------------------------------------------------------
# Module-level shared state (mirrors original search.py top-level globals)
# ---------------------------------------------------------------------------

_repository = SearchRepository()
_loaded_projects, _loaded_saved_searches, _loaded_counters, _next_number = (
    _repository.load_state()
)
for _project in _loaded_projects.values():
    if _project.workflow is None and _project.requested_workflow:
        if get_workflow(_project.requested_workflow):
            _project.workflow = _project.requested_workflow
search_index = SearchIndex(_loaded_projects, _next_number)
projects: Dict[str, ProjectModel] = search_index.projects
saved_searches: Dict[str, SavedSearch] = dict(_loaded_saved_searches)
search_counter: Counter[str] = Counter(_loaded_counters)
project_lock = threading.Lock()
saved_search_lock = threading.Lock()
counter_lock = threading.Lock()
index_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _persist_project(project: ProjectModel, *, next_project_number: int | None = None) -> None:
    """Write ``project`` to persistent storage."""
    _repository.save_project(project, next_project_number=next_project_number)


def _reload_state_from_repository() -> None:
    """Hydrate in-memory state from the persistent repository."""
    loaded_projects, loaded_saved, loaded_counters, next_number = _repository.load_state()
    for project in loaded_projects.values():
        if project.workflow is None and project.requested_workflow:
            if get_workflow(project.requested_workflow):
                project.workflow = project.requested_workflow
    with project_lock:
        search_index.projects.clear()
        search_index.projects.update(loaded_projects)
        search_index._next_project_number = next_number
    with saved_search_lock:
        saved_searches.clear()
        saved_searches.update(loaded_saved)
    with counter_lock:
        search_counter.clear()
        search_counter.update(loaded_counters)


def _reset_state_for_testing(*, db_path: str | None = None) -> None:
    """Clear persistent storage and reload defaults (testing helper)."""
    global _repository

    if db_path is not None:
        _repository = SearchRepository(str(db_path))

    with _repository._lock:
        with _repository._connection() as conn:
            conn.execute("DELETE FROM projects")
            conn.execute("DELETE FROM saved_searches")
            conn.execute("DELETE FROM counters")
            conn.execute(
                "DELETE FROM metadata WHERE key = ?",
                (SearchRepository._NEXT_PROJECT_NUMBER_KEY,),
            )
    with index_lock:
        search_index.index.clear()
    _reload_state_from_repository()


# ---------------------------------------------------------------------------
# Project operations
# ---------------------------------------------------------------------------


def next_project_number() -> int:
    """Return the next sequential project number."""
    with project_lock:
        num = search_index._next_project_number
        search_index._next_project_number += 1
        _repository.set_next_project_number(search_index._next_project_number)
        return num


def add_project(project: ProjectModel) -> None:
    """Store a project in memory."""
    with project_lock:
        if project.updated is None:
            project.updated = datetime.now(UTC)
        if project.workflow and not project.requested_workflow:
            project.requested_workflow = project.workflow
        search_index.add_project(project)
        _persist_project(project, next_project_number=search_index._next_project_number)


def update_project(
    project_id: str,
    *,
    name: str | None = None,
    user: str | None = None,
    doc_type: str | None = None,
    description: str | None = None,
    initial_phase: str | None = None,
    workflow: str | None = None,
    workflow_set: bool = False,
    nara_schedule_number: str | None = None,
    nara_disposition_authority: str | None = None,
    nara_retention_period: str | None = None,
    nara_record_series: str | None = None,
) -> ProjectModel:
    """Update basic fields of a project and return the updated model."""
    with project_lock:
        project = projects[project_id]
        if name is not None:
            project.name = name
        if user is not None:
            project.user = user
        if doc_type is not None:
            project.doc_type = doc_type
        if description is not None:
            project.description = description
        if initial_phase is not None:
            project.initial_phase = initial_phase
        if workflow_set:
            project.workflow = workflow
            project.requested_workflow = workflow
        elif workflow is not None:
            project.workflow = workflow
            project.requested_workflow = workflow
        if nara_schedule_number is not None:
            project.nara_schedule_number = nara_schedule_number
        if nara_disposition_authority is not None:
            project.nara_disposition_authority = nara_disposition_authority
        if nara_retention_period is not None:
            project.nara_retention_period = nara_retention_period
        if nara_record_series is not None:
            project.nara_record_series = nara_record_series
        project.updated = datetime.now(UTC)
        _persist_project(project)
        return project


def add_project_reviewer(project_id: str, reviewer: str) -> ProjectModel:
    """Add a reviewer to a project and sync workflow approvals."""
    from ..approvals import create_approval, list_approvals
    from ..workflows import assign_reviewer

    with project_lock:
        project = projects[project_id]
        if reviewer not in project.reviewers:
            project.reviewers.append(reviewer)
            project.updated = datetime.now(UTC)
            _persist_project(project)

    if project.workflow:
        assign_reviewer(project.workflow, reviewer)
        workflow = get_workflow(project.workflow)
        approvals = list_approvals(project.workflow)
        if not any(a.reviewer == reviewer for a in approvals):
            doc_id = workflow.document if workflow and workflow.document else project.workflow
            phase_id = workflow.phase if workflow else None
            create_approval(
                project.workflow,
                reviewer,
                doc_id,
                description="Reviewer",
                phase_id=phase_id,
                role="Reviewer",
            )
    return project


def update_project_reviewer(project_id: str, reviewer: str, new_reviewer: str) -> ProjectModel:
    """Update a reviewer assignment for a project."""
    from ..approvals import list_approvals
    from ..workflows import assign_reviewer

    with project_lock:
        project = projects[project_id]
        if reviewer not in project.reviewers:
            raise KeyError(reviewer)
        next_reviewers = [
            new_reviewer if value == reviewer else value for value in project.reviewers
        ]
        project.reviewers = list(dict.fromkeys(next_reviewers))
        project.updated = datetime.now(UTC)
        _persist_project(project)

    if project.workflow:
        assign_reviewer(project.workflow, new_reviewer)
        workflow = get_workflow(project.workflow)
        for approval in list_approvals(project.workflow):
            if approval.reviewer == reviewer:
                approval.reviewer = new_reviewer
                if approval.role == reviewer:
                    approval.role = new_reviewer
                if workflow and approval.document_id != workflow.document and workflow.document:
                    approval.document_id = workflow.document
    return project


def remove_project_reviewer(project_id: str, reviewer: str) -> ProjectModel:
    """Remove a reviewer from a project and cleanup approvals."""
    from ..approvals import delete_approval, list_approvals

    with project_lock:
        project = projects[project_id]
        if reviewer not in project.reviewers:
            raise KeyError(reviewer)
        project.reviewers = [value for value in project.reviewers if value != reviewer]
        project.updated = datetime.now(UTC)
        _persist_project(project)

    if project.workflow:
        workflow = get_workflow(project.workflow)
        if workflow and reviewer in workflow.reviewers:
            workflow.reviewers = [value for value in workflow.reviewers if value != reviewer]
        for approval in list_approvals(project.workflow):
            if approval.reviewer == reviewer:
                delete_approval(approval.id)
    return project


def remove_project(project_id: str) -> ProjectModel:
    """Remove a project from memory and persistent storage."""
    with project_lock:
        project = projects.pop(project_id, None)
        if project is None:
            raise KeyError(project_id)
        _repository.delete_project(project_id)
        return project


def add_document(document: object) -> None:
    """Index a document for search."""
    search_index.add_document(document)


def save_search(query: str, user: str) -> SavedSearch:
    """Store a search query for later reuse."""
    if not query.strip():
        raise ValueError("query must not be empty")
    if not user or not user.strip():
        raise ValueError("user must not be empty")

    with saved_search_lock:
        search_id = str(len(saved_searches) + 1)
        record = SavedSearch(id=search_id, query=query, user=user, flagged_for_review=False)
        saved_searches[search_id] = record
        _repository.save_saved_search(record)
        log_event(
            "saved_search_created",
            user_id=user,
            entity_id=search_id,
            entity_type="saved_search",
            query=query,
        )
        return record


def list_saved_searches(user: str | None = None) -> list[SavedSearch]:
    """Return all saved searches optionally filtered by user."""
    with saved_search_lock:
        if user is None:
            return list(saved_searches.values())
        return [s for s in saved_searches.values() if s.user == user]


def search_stats() -> Dict[str, int]:
    """Return recorded search counts per query."""
    with counter_lock:
        return dict(search_counter)


def get_project(project_id: str) -> ProjectModel | None:
    """Return a project and handle expired temporary assignments."""
    with project_lock:
        project = projects.get(project_id)
        if project is not None:
            _expire_temp_assignment(project, lock_held=True)
        return project


def set_project_priority(project_id: str, priority: int) -> ProjectModel:
    """Update a project's priority level."""
    with project_lock:
        project = projects[project_id]
        project.priority = priority
        _persist_project(project)
        return project


def assign_temporary(
    project_id: str, user: str, until: datetime, *, approved: bool = False
) -> ProjectModel:
    """Temporarily assign a project to another user with optional approval."""
    if until.tzinfo is None:
        until = until.replace(tzinfo=UTC)
    with project_lock:
        project = projects[project_id]
        remaining = until - datetime.now(UTC)
        if remaining > timedelta(days=TEMP_ASSIGN_MAX_DAYS) and not approved:
            raise ValueError("Manager approval required for long assignment")
        project.temp_user = user
        project.temp_until = until
        _persist_project(project)
        return project


def _expire_temp_assignment(project: ProjectModel, *, lock_held: bool = False) -> None:
    """Clear ``project.temp_user`` when the temporary period has ended."""
    if not project.temp_user or not project.temp_until:
        return

    until = project.temp_until
    if until.tzinfo is None:
        until = until.replace(tzinfo=UTC)

    if datetime.now(UTC) < until:
        return

    changed = False
    if lock_held:
        project.temp_user = None
        project.temp_until = None
        changed = True
    else:
        with project_lock:
            project.temp_user = None
            project.temp_until = None
            changed = True
    if changed:
        _persist_project(project)


def list_projects(user: str | None = None) -> list[ProjectModel]:
    """Return projects optionally filtered by assigned user."""
    from ..approvals import list_approvals

    with project_lock:
        result = []
        for proj in projects.values():
            _expire_temp_assignment(proj, lock_held=True)

            if user is None or proj.user == user or proj.temp_user == user:
                result.append(proj)
                continue

            if user and user in proj.reviewers:
                result.append(proj)
                continue

            if user and proj.workflow:
                workflow_approvals = list_approvals(proj.workflow)
                for approval in workflow_approvals:
                    if approval.reviewer == user:
                        result.append(proj)
                        break

        return result


def overdue_high_priority() -> list[str]:
    """Return IDs of high priority projects that are overdue."""
    with project_lock:
        alerts: list[str] = []
        for proj in projects.values():
            _expire_temp_assignment(proj, lock_held=True)
            created = proj.created
            if created.tzinfo is None:
                created = created.replace(tzinfo=UTC)
            if proj.priority >= 5 and created < datetime.now(UTC) - timedelta(days=14):
                alerts.append(proj.id)
        return alerts


def _candidate_ids(terms: list[str]) -> set[str]:
    """Return document IDs potentially matching ``terms``."""
    from .. import fts

    try:
        candidates = set(fts.search(" ".join(terms)))
    except Exception:
        candidates = set()
    for term in terms:
        with index_lock:
            candidates.update(search_index.index.get(term, set()))
    return candidates


def _matches(
    doc: Any,
    terms: list[str],
    *,
    project: str | None,
    user: str | None,
    priority: int | None,
    after: datetime | None,
    before: datetime | None,
) -> bool:
    text = doc.content
    if doc.project and doc.project in projects:
        with project_lock:
            text += " " + projects[doc.project].name
    if not _match_all_terms(text, terms):
        return False
    if project and doc.project != project:
        return False
    if user and doc.user != user:
        return False
    if priority is not None and doc.priority != priority:
        return False
    if after and (doc.date is None or doc.date < after):
        return False
    if before and (doc.date is None or doc.date > before):
        return False
    return True


def search(
    query: str,
    *,
    project: Optional[str] = None,
    user: Optional[str] = None,
    priority: Optional[int] = None,
    after: datetime | None = None,
    before: datetime | None = None,
) -> List[Any]:
    """Return documents matching the query and optional filters."""
    from ..cache import cache_delete, cache_get, cache_set
    from ..documents import DocumentModel, documents as _documents

    import json as _json

    with counter_lock:
        search_counter[query] += 1
        _repository.increment_counter(query)
    cache_key = (
        f"search-core-{query}-{project or ''}-{user or ''}-"
        f"{priority if priority is not None else ''}-"
        f"{after.isoformat() if after else ''}-"
        f"{before.isoformat() if before else ''}"
    )
    cached = cache_get(cache_key)
    if cached:
        try:
            if isinstance(cached, bytes):
                cached = cached.decode()
            data = _json.loads(cached)
            return [DocumentModel.model_validate(d) for d in data]
        except Exception:
            cache_delete(cache_key)
    terms = _normalize(query).split()
    if not terms:
        candidate_ids = set(_documents.keys())
    else:
        candidate_ids = _candidate_ids(terms)

    results: List[Any] = []
    for doc_id in candidate_ids:
        doc = _documents.get(doc_id)
        if doc is None:
            continue
        if _matches(
            doc,
            terms,
            project=project,
            user=user,
            priority=priority,
            after=after,
            before=before,
        ):
            results.append(doc)

    cache_set(
        cache_key,
        _json.dumps([d.model_dump(mode="json") for d in results]),
        ttl=30,
    )
    return results


def ranked_search(query: str, docs: list[Any] | None = None) -> List[dict[str, Any]]:
    """Return search results with simple ranking and preview snippets."""
    terms = _normalize(query).split()
    base = docs if docs is not None else search(query)

    def score(doc: Any) -> int:
        return sum(doc.content.lower().count(t) for t in terms)

    def snippet(doc: Any) -> str:
        if not terms:
            return doc.content[:30]
        idx = doc.content.lower().find(terms[0])
        if idx == -1:
            return doc.content[:30]
        return doc.content[idx: idx + 30]

    ranked = sorted(base, key=score, reverse=True)
    return [{"document": doc, "snippet": snippet(doc), "score": score(doc)} for doc in ranked]


# ---------------------------------------------------------------------------
# search_documents alias for backward compat / tests
# ---------------------------------------------------------------------------


def search_documents(
    query: str,
    *,
    project: Optional[str] = None,
    user: Optional[str] = None,
    priority: Optional[int] = None,
    after: datetime | None = None,
    before: datetime | None = None,
) -> List[Any]:
    """Alias for :func:`search` for backward compatibility."""
    return search(
        query,
        project=project,
        user=user,
        priority=priority,
        after=after,
        before=before,
    )


__all__ = [
    # models
    "ProjectModel",
    "SavedSearch",
    "DEFAULT_PROJECT_ID",
    # indexing
    "SearchRepository",
    "SearchIndex",
    "search_index",
    "projects",
    "saved_searches",
    "search_counter",
    "project_lock",
    "saved_search_lock",
    "counter_lock",
    "index_lock",
    # query / operations
    "TEMP_ASSIGN_MAX_DAYS",
    "search",
    "search_documents",
    "ranked_search",
    "add_document",
    "add_project",
    "update_project",
    "remove_project",
    "get_project",
    "list_projects",
    "set_project_priority",
    "assign_temporary",
    "next_project_number",
    "add_project_reviewer",
    "update_project_reviewer",
    "remove_project_reviewer",
    "overdue_high_priority",
    "save_search",
    "list_saved_searches",
    "search_stats",
    # external search
    "ExternalSearchClient",
    "get_external_url",
    "get_search_backend",
    "is_external_search_configured",
    # internal helpers re-exported for backward compat
    "_repository",
    "_normalize",
    "_match_all_terms",
    "_candidate_ids",
    "_matches",
    "_expire_temp_assignment",
    "_persist_project",
    "_reload_state_from_repository",
    "_reset_state_for_testing",
    "_default_project",
]

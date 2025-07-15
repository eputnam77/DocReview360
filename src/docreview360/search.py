from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
import json

from .cache import cache_get, cache_set

from pydantic import BaseModel

from . import fts
from .documents import DocumentModel, documents


class ProjectModel(BaseModel):
    """Representation of a project with assignment metadata."""

    id: str
    name: str
    number: int | None = None
    user: Optional[str] = None
    priority: int = 0
    created: datetime = datetime.utcnow()
    temp_user: Optional[str] = None
    temp_until: datetime | None = None


@dataclass
class SavedSearch:
    """Representation of a saved search query."""

    id: str
    query: str
    user: str | None = None
    created: datetime = datetime.utcnow()
    count: int = 0


class SearchIndex:
    """Simple in-memory inverted index for documents."""

    def __init__(self) -> None:
        self._next_project_number = 1
        default = ProjectModel(id="1", name="Example", number=self._next_project_number)
        self._next_project_number += 1
        self.projects: Dict[str, ProjectModel] = {"1": default}
        self.index: Dict[str, Set[str]] = {}

    def add_project(self, project: ProjectModel) -> None:
        """Store a project and update indexes."""
        if project.number is None:
            project.number = self._next_project_number
            self._next_project_number += 1
        self.projects[project.id] = project

    def add_document(self, document: DocumentModel) -> None:
        """Index tokens from the document and associated project."""
        tokens = _normalize(document.content).split()
        if document.project and document.project in self.projects:
            tokens += _normalize(self.projects[document.project].name).split()
        for token in tokens:
            self.index.setdefault(token, set()).add(document.id)

    def remove_document(self, doc_id: str) -> None:
        """Remove a document from the index."""
        for ids in self.index.values():
            ids.discard(doc_id)


search_index = SearchIndex()
projects = search_index.projects
saved_searches: Dict[str, SavedSearch] = {}
search_counter: Counter[str] = Counter()


def next_project_number() -> int:
    """Return the next sequential project number."""
    num = search_index._next_project_number
    search_index._next_project_number += 1
    return num


def add_project(project: ProjectModel) -> None:
    """Store a project in memory."""
    search_index.add_project(project)


def add_document(document: DocumentModel) -> None:
    """Index a document for search."""
    search_index.add_document(document)


def save_search(query: str, user: str | None = None) -> SavedSearch:
    """Store a search query for later reuse.

    Parameters
    ----------
    query:
        Raw search string which must not be empty.
    user:
        Optional username used for scoping saved searches.

    Returns
    -------
    SavedSearch
        The created search record containing the assigned id.
    """

    if not query.strip():
        raise ValueError("query must not be empty")

    search_id = str(len(saved_searches) + 1)
    record = SavedSearch(id=search_id, query=query, user=user)
    saved_searches[search_id] = record
    return record


def list_saved_searches(user: str | None = None) -> list[SavedSearch]:
    """Return all saved searches optionally filtered by user."""
    if user is None:
        return list(saved_searches.values())
    return [s for s in saved_searches.values() if s.user == user]


def search_stats() -> Dict[str, int]:
    """Return recorded search counts per query."""
    return dict(search_counter)


def get_project(project_id: str) -> ProjectModel | None:
    """Return a project and handle expired temporary assignments."""
    project = projects.get(project_id)
    if project is not None:
        _expire_temp_assignment(project)
    return project


def set_project_priority(project_id: str, priority: int) -> ProjectModel:
    """Update a project's priority level."""
    project = projects[project_id]
    project.priority = priority
    return project


TEMP_ASSIGN_MAX_DAYS = 30


def assign_temporary(
    project_id: str, user: str, until: datetime, *, approved: bool = False
) -> ProjectModel:
    """Temporarily assign a project to another user with optional approval.

    The ``until`` timestamp may be in the past to immediately expire the
    temporary assignment.  Long assignments beyond ``TEMP_ASSIGN_MAX_DAYS``
    require ``approved`` to be ``True``.
    """
    project = projects[project_id]
    if (until - datetime.utcnow()).days > TEMP_ASSIGN_MAX_DAYS and not approved:
        raise ValueError("Manager approval required for long assignment")
    project.temp_user = user
    project.temp_until = until
    return project


def _expire_temp_assignment(project: ProjectModel) -> None:
    """Clear ``project.temp_user`` when the temporary period has ended."""
    if project.temp_user and project.temp_until and datetime.utcnow() >= project.temp_until:
        project.temp_user = None
        project.temp_until = None


def list_projects(user: str | None = None) -> list[ProjectModel]:
    """Return projects optionally filtered by assigned user."""
    result = []
    for proj in projects.values():
        _expire_temp_assignment(proj)
        if user is None or proj.user == user or proj.temp_user == user:
            result.append(proj)
    return result


def overdue_high_priority() -> list[str]:
    """Return IDs of high priority projects that are overdue."""
    alerts: list[str] = []
    for proj in projects.values():
        _expire_temp_assignment(proj)
        if proj.priority >= 5 and proj.created < datetime.utcnow() - timedelta(days=14):
            alerts.append(proj.id)
    return alerts


def _normalize(text: str) -> str:
    """Return a whitespace-normalised lowercase string."""

    cleaned = re.sub(r"[^\w]+", " ", text)
    return cleaned.lower().strip()


def _match_all_terms(text: str, terms: list[str]) -> bool:
    """Return ``True`` if all ``terms`` are present in ``text``."""
    normalized = _normalize(text)
    return all(term in normalized for term in terms)


def _candidate_ids(terms: list[str]) -> set[str]:
    """Return document IDs potentially matching ``terms``."""
    try:
        candidates = set(fts.search(" ".join(terms)))
    except Exception:
        candidates = set()
    for term in terms:
        candidates.update(search_index.index.get(term, set()))
    return candidates


def _matches(
    doc: DocumentModel,
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
) -> List[DocumentModel]:
    """Return documents matching the query and optional filters.

    Results are cached via :mod:`docreview360.cache` to avoid repeated
    computation. The cache key includes all filter parameters so callers
    receive up‑to‑date results when any input changes. Cached entries expire
    after 30 seconds.
    """
    search_counter[query] += 1
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
            data = json.loads(cached)
            return [DocumentModel.model_validate(d) for d in data]
        except Exception:  # pragma: no cover - fallback to recompute
            pass
    terms = _normalize(query).split()
    if not terms:
        candidate_ids = set(documents.keys())
    else:
        candidate_ids = _candidate_ids(terms)

    results: List[DocumentModel] = []
    for doc_id in candidate_ids:
        doc = documents.get(doc_id)
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
        json.dumps([d.model_dump(mode="json") for d in results]),
        ttl=30,
    )
    return results


def ranked_search(query: str, docs: list[DocumentModel] | None = None) -> List[dict[str, Any]]:
    """Return search results with simple ranking and preview snippets."""
    terms = _normalize(query).split()
    base = docs if docs is not None else search(query)

    def score(doc: DocumentModel) -> int:
        return sum(doc.content.lower().count(t) for t in terms)

    def snippet(doc: DocumentModel) -> str:
        if not terms:
            return doc.content[:30]
        idx = doc.content.lower().find(terms[0])
        if idx == -1:
            return doc.content[:30]
        return doc.content[idx : idx + 30]

    ranked = sorted(base, key=score, reverse=True)
    return [{"document": doc, "snippet": snippet(doc), "score": score(doc)} for doc in ranked]

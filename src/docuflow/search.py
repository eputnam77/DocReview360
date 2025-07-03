from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel

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
    """Temporarily assign a project to another user with optional approval."""
    project = projects[project_id]
    if (until - datetime.utcnow()).days > TEMP_ASSIGN_MAX_DAYS and not approved:
        raise ValueError("Manager approval required for long assignment")
    project.temp_user = user
    project.temp_until = until
    return project


def _expire_temp_assignment(project: ProjectModel) -> None:
    if project.temp_user and project.temp_until and datetime.utcnow() >= project.temp_until:
        project.temp_user = None
        project.temp_until = None


def list_projects() -> list[ProjectModel]:
    """Return all projects."""
    for proj in projects.values():
        _expire_temp_assignment(proj)
    return list(projects.values())


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
    normalized = _normalize(text)
    return all(term in normalized for term in terms)


def search(
    query: str,
    *,
    project: Optional[str] = None,
    user: Optional[str] = None,
    priority: Optional[int] = None,
    after: datetime | None = None,
    before: datetime | None = None,
) -> List[DocumentModel]:
    """Return documents matching the query and optional filters."""
    terms = _normalize(query).split()
    if not terms:
        candidate_ids = set(documents.keys())
    else:
        candidate_ids: Set[str] | None = None
        for term in terms:
            ids = search_index.index.get(term, set())
            candidate_ids = ids if candidate_ids is None else candidate_ids & ids
        candidate_ids = candidate_ids or set()

    results: List[DocumentModel] = []
    for doc_id in candidate_ids:
        doc = documents.get(doc_id)
        if doc is None:
            continue
        if project and doc.project != project:
            continue
        if user and doc.user != user:
            continue
        if priority is not None and doc.priority != priority:
            continue
        if after and (doc.date is None or doc.date < after):
            continue
        if before and (doc.date is None or doc.date > before):
            continue
        results.append(doc)

    return results


def ranked_search(query: str) -> List[dict[str, Any]]:
    """Return search results with simple ranking and preview snippets."""
    terms = _normalize(query).split()
    base = search(query)

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

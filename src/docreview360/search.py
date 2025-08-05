"""Naïve in-memory search index."""

from __future__ import annotations

import json
import re
import threading
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, computed_field

from . import fts
from .cache import cache_get, cache_set
from .documents import DocumentModel, documents
from .workflows import get_workflow
import uuid


class ProjectModel(BaseModel):
    """Representation of a project with assignment metadata."""

    id: str
    name: str
    number: int | None = None
    document_number: str | None = None  # User-provided document number/reference
    user: Optional[str] = None
    doc_type: str | None = None
    workflow: str | None = None
    priority: int = 0
    created: datetime = datetime.now(UTC)
    temp_user: Optional[str] = None
    temp_until: datetime | None = None
    updated: datetime | None = None  # Add updated field for frontend compatibility

    @computed_field
    @property
    def status(self) -> str:
        """Derive status from workflow phase or return default."""
        if self.workflow:
            wf = get_workflow(self.workflow)
            if wf:
                # Map workflow phases to status values
                phase = wf.phase.lower()
                if "draft" in phase or "initial" in phase:
                    return "Draft"
                elif "review" in phase:
                    return "In Progress"
                elif "public comment" in phase:
                    return "In Progress"  # Map Public Comment to In Progress
                elif "approval" in phase or "final" in phase:
                    return "Complete"
                elif "overdue" in phase:
                    return "Overdue"
                else:
                    return wf.phase
        return "Draft"  # Default status for projects without workflows

    @computed_field
    @property
    def title(self) -> str:
        """Alias for name field for frontend compatibility."""
        return self.name

    @computed_field
    @property
    def type(self) -> str:
        """Alias for doc_type field for frontend compatibility."""
        return self.doc_type or "Unknown"

    @computed_field
    @property
    def progress(self) -> int:
        """Calculate progress based on workflow status."""
        if self.workflow:
            wf = get_workflow(self.workflow)
            if wf:
                # Simple progress calculation based on workflow phase
                phase = wf.phase.lower()
                if "draft" in phase or "initial" in phase:
                    return 10
                elif "review" in phase:
                    return 50
                elif "public comment" in phase:
                    return 75
                elif "approval" in phase or "final" in phase:
                    return 90
                else:
                    return 25
        return 0  # Default progress for projects without workflows


@dataclass
class SavedSearch:
    """Representation of a saved search query."""

    id: str
    query: str
    user: str | None = None
    created: datetime = datetime.now(UTC)
    count: int = 0


class SearchIndex:
    """Simple in-memory inverted index for documents."""

    def __init__(self) -> None:
        self._next_project_number = 1
        # Generate a proper UUID for the default project
        default_id = str(uuid.uuid4())
        current_time = datetime.now(UTC)
        default = ProjectModel(
            id=default_id, 
            name="Example", 
            number=self._next_project_number,
            document_number="1",  # Legacy support
            updated=current_time
        )
        self._next_project_number += 1
        self.projects: Dict[str, ProjectModel] = {default_id: default}
        self.index: Dict[str, Set[str]] = {}

    def add_project(self, project: ProjectModel) -> None:
        """Store a project and update indexes."""
        if project.number is None:
            project.number = self._next_project_number
            self._next_project_number += 1
        # Set updated field to current time if not already set
        if project.updated is None:
            project.updated = datetime.now(UTC)
        self.projects[project.id] = project

    def generate_project_id(self) -> str:
        """Generate a unique project ID."""
        return str(uuid.uuid4())

    def add_document(self, document: DocumentModel) -> None:
        """Index tokens from the document and associated project."""
        tokens = _normalize(document.content).split()
        if document.project and document.project in self.projects:
            tokens += _normalize(self.projects[document.project].name).split()
        with index_lock:
            for token in tokens:
                self.index.setdefault(token, set()).add(document.id)

    def remove_document(self, doc_id: str) -> None:
        """Remove a document from the index."""
        with index_lock:
            for ids in self.index.values():
                ids.discard(doc_id)


search_index = SearchIndex()
projects = search_index.projects
saved_searches: Dict[str, SavedSearch] = {}
search_counter: Counter[str] = Counter()
project_lock = threading.Lock()
index_lock = threading.Lock()


def next_project_number() -> int:
    """Return the next sequential project number."""
    with project_lock:
        num = search_index._next_project_number
        search_index._next_project_number += 1
        return num


def add_project(project: ProjectModel) -> None:
    """Store a project in memory."""
    with project_lock:
        # Set updated field to current time if not already set
        if project.updated is None:
            project.updated = datetime.now(UTC)
        search_index.add_project(project)


def update_project(
    project_id: str,
    *,
    name: str | None = None,
    user: str | None = None,
    doc_type: str | None = None,
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
        # Update the updated timestamp
        project.updated = datetime.now(UTC)
        return project


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
    with project_lock:
        project = projects[project_id]
        if (until - datetime.now(UTC)).days > TEMP_ASSIGN_MAX_DAYS and not approved:
            raise ValueError("Manager approval required for long assignment")
        project.temp_user = user
        project.temp_until = until
        return project


def _expire_temp_assignment(project: ProjectModel, *, lock_held: bool = False) -> None:
    """Clear ``project.temp_user`` when the temporary period has ended."""
    if project.temp_user and project.temp_until and datetime.now(UTC) >= project.temp_until:
        if lock_held:
            # Lock is already held by caller, modify directly
            project.temp_user = None
            project.temp_until = None
        else:
            # Acquire lock before modifying
            with project_lock:
                project.temp_user = None
                project.temp_until = None


def list_projects(user: str | None = None) -> list[ProjectModel]:
    """Return projects optionally filtered by assigned user.
    
    Includes projects where the user is:
    1. Directly assigned as project.user
    2. Temporarily assigned as project.temp_user  
    3. Assigned as a reviewer in any approval step
    """
    from .approvals import list_approvals
    
    with project_lock:
        result = []
        for proj in projects.values():
            _expire_temp_assignment(proj, lock_held=True)
            
            # Check direct assignments
            if user is None or proj.user == user or proj.temp_user == user:
                result.append(proj)
                continue
                
            # Check approval assignments if user is specified and project has workflow
            if user and proj.workflow:
                # Get all approvals for this project's workflow
                workflow_approvals = list_approvals(proj.workflow)
                # Check if user is assigned as a reviewer in any approval
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
            if proj.priority >= 5 and proj.created < datetime.now(UTC) - timedelta(days=14):
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
        with index_lock:
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

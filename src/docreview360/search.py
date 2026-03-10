# SPDX-License-Identifier: MIT
"""Search index module backed by a lightweight persistent store."""

from __future__ import annotations

import atexit
import json
import logging
import os
import re
import sqlite3
import threading
import uuid
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field, computed_field, model_validator

from . import fts
from .cache import cache_delete, cache_get, cache_set
from .documents import DocumentModel, documents
from .logs import log_event
from .workflows import get_workflow

logger = logging.getLogger(__name__)


class ProjectModel(BaseModel):
    """Representation of a project with assignment metadata."""

    id: str
    name: str
    number: int | None = None
    document_number: str | None = None  # User-provided document number/reference
    user: Optional[str] = None
    # Organization identifier for multi-tenant isolation.
    # When set, access control is enforced so only users in the same org
    # (or admins) can read or modify this project.
    org_id: int | None = None
    doc_type: str | None = None
    workflow: str | None = None
    requested_workflow: str | None = None
    priority: int = 0
    created: datetime = Field(default_factory=lambda: datetime.now(UTC))
    temp_user: Optional[str] = None
    temp_until: datetime | None = None
    updated: datetime | None = None  # Add updated field for frontend compatibility
    description: str | None = None
    reviewers: List[str] = Field(default_factory=list)
    # Store the initially requested phase even when no workflow is associated.
    # This allows the API to surface a project's phase before a workflow has
    # been created.
    initial_phase: str | None = None

    @computed_field
    def created_at(self) -> datetime:
        """Expose ``created`` under a ``created_at`` alias for API consistency."""
        return self.created

    @computed_field
    def phase(self) -> str | None:
        """Return the current workflow phase, if any.

        This surfaces the active phase for a project so the edit form can
        populate its Phase field based on the associated workflow.
        """
        if self.workflow:
            wf = get_workflow(self.workflow)
            if wf:
                return wf.phase
        return self.initial_phase

    @computed_field
    def current_phase_id(self) -> str | None:
        """Expose the raw phase identifier for API consumers."""
        if self.workflow:
            wf = get_workflow(self.workflow)
            if wf:
                return wf.phase
        return self.initial_phase

    @computed_field
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
                    return "In Progress"  # Map Public Comment / Proposed Rulemaking to In Progress
                elif "approval" in phase or "final" in phase:
                    return "Complete"
                elif "overdue" in phase:
                    return "Overdue"
                else:
                    return wf.phase
        return "Draft"  # Default status for projects without workflows

    @computed_field
    def title(self) -> str:
        """Alias for name field for frontend compatibility."""
        return self.name

    @computed_field
    def type(self) -> str:
        """Alias for doc_type field for frontend compatibility."""
        return self.doc_type or "Unknown"

    @computed_field
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

    @model_validator(mode="after")
    def _ensure_requested_workflow(self) -> "ProjectModel":
        if self.requested_workflow is None and self.workflow:
            self.requested_workflow = self.workflow
        return self


@dataclass
class SavedSearch:
    """Representation of a saved search query."""

    id: str
    query: str
    user: str
    created: datetime = field(default_factory=lambda: datetime.now(UTC))
    count: int = 0
    flagged_for_review: bool = False


DEFAULT_PROJECT_ID = "demo-project"


def _default_project(project_number: int) -> ProjectModel:
    """Return a default demo project for bootstrapping the system."""

    current_time = datetime.now(UTC)
    return ProjectModel(
        id=DEFAULT_PROJECT_ID,
        name="Demo Project",
        number=project_number,
        document_number="DOC-001",
        user="alice",
        doc_type="General Memorandum",
        updated=current_time,
    )


class SearchRepository:
    """SQLite-backed persistence for the search module."""

    _NEXT_PROJECT_NUMBER_KEY = "next_project_number"

    def __init__(self, path: str | None = None) -> None:
        env_path = path or os.getenv("DOCREVIEW360_SEARCH_DB")
        if env_path:
            self._path = Path(env_path).expanduser()
        else:
            base_dir = os.getenv("DOCREVIEW360_DATA_DIR")
            base_path = Path(base_dir).expanduser() if base_dir else Path.cwd()
            self._path = base_path / "search_state.db"
        if not self._path.parent.exists():
            self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._local = threading.local()
        self._connections: set[sqlite3.Connection] = set()
        atexit.register(self.close)
        with self._connection() as conn:
            self._initialize(conn)

    @contextmanager
    def _connection(self) -> sqlite3.Connection:
        with self._lock:
            conn = getattr(self._local, "connection", None)
            if conn is None:
                conn = sqlite3.connect(self._path, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                try:
                    conn.execute("PRAGMA journal_mode=WAL")
                except sqlite3.DatabaseError:
                    pass
                self._local.connection = conn
                self._connections.add(conn)
        try:
            yield conn
            conn.commit()
        finally:
            pass

    def close(self) -> None:
        """Close any cached sqlite connections."""
        with self._lock:
            connections = list(self._connections)
            self._connections.clear()
            if hasattr(self._local, "connection"):
                delattr(self._local, "connection")
        for conn in connections:
            try:
                conn.close()
            except sqlite3.DatabaseError:
                pass

    def _initialize(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS saved_searches (
                id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                user TEXT,
                created TEXT NOT NULL,
                count INTEGER NOT NULL,
                flagged INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS counters (
                query TEXT PRIMARY KEY,
                count INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        self._ensure_saved_search_schema(conn)
        self._backfill_saved_search_users(conn)

    def _ensure_saved_search_schema(self, conn: sqlite3.Connection) -> None:
        """Ensure optional columns for saved searches are present."""

        info = conn.execute("PRAGMA table_info(saved_searches)").fetchall()
        column_names = {row["name"] for row in info}
        if "flagged" not in column_names:
            conn.execute("ALTER TABLE saved_searches ADD COLUMN flagged INTEGER NOT NULL DEFAULT 0")

    def _backfill_saved_search_users(self, conn: sqlite3.Connection) -> None:
        """Assign a placeholder user for legacy saved searches without one."""

        conn.execute(
            """
            UPDATE saved_searches
            SET user = 'unknown',
                flagged = 1
            WHERE user IS NULL OR TRIM(user) = ''
            """
        )

    def load_state(
        self,
    ) -> tuple[dict[str, ProjectModel], dict[str, SavedSearch], Counter[str], int]:
        """Return persisted projects, saved searches, counters, and next number."""

        with self._lock:
            with self._connection() as conn:
                project_rows = conn.execute("SELECT id, payload FROM projects").fetchall()
                projects: dict[str, ProjectModel] = {}
                missing_workflows: list[tuple[str, str]] = []
                for row in project_rows:
                    project = ProjectModel.model_validate_json(row["payload"])
                    if project.requested_workflow is None and project.workflow:
                        project.requested_workflow = project.workflow
                    if project.workflow and not get_workflow(project.workflow):
                        missing_workflows.append((project.id, project.workflow))
                    projects[project.id] = project

                for project_id, workflow_id in missing_workflows:
                    logger.warning(
                        "Project %s referenced missing workflow %s; clearing workflow pointer",
                        project_id,
                        workflow_id,
                    )
                    project = projects[project_id]
                    project.requested_workflow = workflow_id
                    project.workflow = None
                    conn.execute(
                        "UPDATE projects SET payload = ? WHERE id = ?",
                        (json.dumps(project.model_dump(mode="json")), project_id),
                    )

                saved_rows = conn.execute(
                    "SELECT id, query, user, created, count, flagged FROM saved_searches"
                ).fetchall()
                saved: dict[str, SavedSearch] = {}
                flagged_searches: list[str] = []
                for row in saved_rows:
                    user = row["user"]
                    flagged = bool(row["flagged"])
                    if not user or not str(user).strip():
                        user = "unknown"
                        flagged = True
                        flagged_searches.append(row["id"])
                        conn.execute(
                            "UPDATE saved_searches SET user = ?, flagged = 1 WHERE id = ?",
                            (user, row["id"]),
                        )
                    saved[row["id"]] = SavedSearch(
                        id=row["id"],
                        query=row["query"],
                        user=user,
                        created=datetime.fromisoformat(row["created"]),
                        count=row["count"],
                        flagged_for_review=flagged,
                    )

                if flagged_searches:
                    logger.warning(
                        "Backfilled creator for saved searches missing attribution: %s",
                        ", ".join(flagged_searches),
                    )

                counter_rows = conn.execute("SELECT query, count FROM counters").fetchall()
                counters = Counter({row["query"]: row["count"] for row in counter_rows})

                next_number = self._read_next_project_number(conn)

        if not projects:
            default = _default_project(1)
            with self._lock:
                self.save_project(default, next_project_number=2)
            projects = {default.id: default}
            next_number = 2
        elif next_number is None:
            next_number = max((p.number or 0 for p in projects.values()), default=0) + 1
            self.set_next_project_number(next_number)

        return projects, saved, counters, next_number

    def save_project(
        self, project: ProjectModel, *, next_project_number: int | None = None
    ) -> None:
        payload = json.dumps(project.model_dump(mode="json"))
        with self._lock:
            with self._connection() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO projects (id, payload) VALUES (?, ?)",
                    (project.id, payload),
                )
                if next_project_number is not None:
                    conn.execute(
                        "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                        (self._NEXT_PROJECT_NUMBER_KEY, str(next_project_number)),
                    )

    def delete_project(self, project_id: str) -> None:
        """Remove a project from persistent storage."""
        with self._lock:
            with self._connection() as conn:
                conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))

    def save_saved_search(self, saved_search: SavedSearch) -> None:
        with self._lock:
            with self._connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO saved_searches (id, query, user, created, count, flagged)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        saved_search.id,
                        saved_search.query,
                        saved_search.user,
                        saved_search.created.isoformat(),
                        saved_search.count,
                        int(saved_search.flagged_for_review),
                    ),
                )

    def increment_counter(self, query: str, delta: int = 1) -> None:
        with self._lock:
            with self._connection() as conn:
                conn.execute(
                    """
                    INSERT INTO counters(query, count) VALUES(?, ?)
                    ON CONFLICT(query) DO UPDATE SET count = count + excluded.count
                    """,
                    (query, delta),
                )

    def set_next_project_number(self, value: int) -> None:
        with self._lock:
            with self._connection() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                    (self._NEXT_PROJECT_NUMBER_KEY, str(value)),
                )

    def _read_next_project_number(self, conn: sqlite3.Connection) -> int | None:
        row = conn.execute(
            "SELECT value FROM metadata WHERE key = ?",
            (self._NEXT_PROJECT_NUMBER_KEY,),
        ).fetchone()
        if not row:
            return None
        try:
            return int(row["value"])
        except (TypeError, ValueError):
            return None


class SearchIndex:
    """Simple in-memory inverted index for documents."""

    def __init__(
        self,
        projects: dict[str, ProjectModel] | None = None,
        next_project_number: int | None = None,
    ) -> None:
        self.index: Dict[str, Set[str]] = {}
        if projects is None:
            projects = {}
        if next_project_number is None:
            next_project_number = (
                max((proj.number or 0 for proj in projects.values()), default=0) + 1
            )
        if not projects:
            default = _default_project(1)
            projects = {default.id: default}
            next_project_number = 2
        self.projects: Dict[str, ProjectModel] = dict(projects)
        self._next_project_number = next_project_number

    def add_project(self, project: ProjectModel) -> None:
        """Store a project and update indexes."""
        if project.number is None:
            project.number = self._next_project_number
            self._next_project_number += 1
        elif project.number >= self._next_project_number:
            self._next_project_number = project.number + 1
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


_repository = SearchRepository()
_loaded_projects, _loaded_saved_searches, _loaded_counters, _next_number = _repository.load_state()
for _project in _loaded_projects.values():
    if _project.workflow is None and _project.requested_workflow:
        if get_workflow(_project.requested_workflow):
            _project.workflow = _project.requested_workflow
search_index = SearchIndex(_loaded_projects, _next_number)
projects = search_index.projects
saved_searches: Dict[str, SavedSearch] = dict(_loaded_saved_searches)
search_counter: Counter[str] = Counter(_loaded_counters)
project_lock = threading.Lock()
saved_search_lock = threading.Lock()
counter_lock = threading.Lock()
index_lock = threading.Lock()


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


def _reset_state_for_testing(*, db_path: str | Path | None = None) -> None:
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
        # Set updated field to current time if not already set
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
        # When the caller explicitly provided the workflow field (even if None),
        # update it accordingly. Otherwise leave it unchanged.
        if workflow_set:
            project.workflow = workflow
            project.requested_workflow = workflow
        elif workflow is not None:
            project.workflow = workflow
            project.requested_workflow = workflow
        # Update the updated timestamp
        project.updated = datetime.now(UTC)
        _persist_project(project)
        return project


def add_project_reviewer(project_id: str, reviewer: str) -> ProjectModel:
    """Add a reviewer to a project and sync workflow approvals."""
    from .approvals import create_approval, list_approvals
    from .workflows import assign_reviewer

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
    from .approvals import list_approvals
    from .workflows import assign_reviewer

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
    from .approvals import delete_approval, list_approvals

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


def add_document(document: DocumentModel) -> None:
    """Index a document for search."""
    search_index.add_document(document)


def save_search(query: str, user: str) -> SavedSearch:
    """Store a search query for later reuse.

    Parameters
    ----------
    query:
        Raw search string which must not be empty.
    user:
        Username used for scoping saved searches.

    Returns
    -------
    SavedSearch
        The created search record containing the assigned id.
    """

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


TEMP_ASSIGN_MAX_DAYS = 30


def assign_temporary(
    project_id: str, user: str, until: datetime, *, approved: bool = False
) -> ProjectModel:
    """Temporarily assign a project to another user with optional approval.

    The ``until`` timestamp may be in the past to immediately expire the
    temporary assignment.  Long assignments beyond ``TEMP_ASSIGN_MAX_DAYS``
    require ``approved`` to be ``True``.
    """
    # ``until`` was previously required to be timezone-aware.  Passing a naive
    # ``datetime`` (common in tests and callers) raised a ``TypeError`` when
    # compared against ``datetime.now(UTC)``.  Treat naive values as UTC to make
    # the helper more forgiving.
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
        # Lock is already held by caller, modify directly
        project.temp_user = None
        project.temp_until = None
        changed = True
    else:
        # Acquire lock before modifying
        with project_lock:
            project.temp_user = None
            project.temp_until = None
            changed = True
    if changed:
        _persist_project(project)


def list_projects(user: str | None = None) -> list[ProjectModel]:
    """Return projects optionally filtered by assigned user.

    Includes projects where the user is:
    1. Directly assigned as project.user
    2. Temporarily assigned as project.temp_user
    3. Listed as a project reviewer
    4. Assigned as a reviewer in any approval step
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

            # Check explicit reviewer assignments
            if user and user in proj.reviewers:
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
            created = proj.created
            if created.tzinfo is None:
                created = created.replace(tzinfo=UTC)
            if proj.priority >= 5 and created < datetime.now(UTC) - timedelta(days=14):
                alerts.append(proj.id)
        return alerts


def _normalize(text: str) -> str:
    """Return a whitespace-normalized lowercase string."""

    cleaned = re.sub(r"[^\w]+", " ", text)
    return cleaned.lower().strip()


def _match_all_terms(text: str, terms: list[str]) -> bool:
    """Return ``True`` if all ``terms`` appear as whole words in ``text``.

    The previous implementation simply performed substring checks which meant a
    search term like ``"cat"`` would match a document containing the word
    ``"scatter"``.  By tokenizing the normalized text we ensure matches respect
    word boundaries and avoid surprising false positives.
    """
    normalized = _normalize(text)
    tokens = set(normalized.split())
    return all(term in tokens for term in terms)


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
            data = json.loads(cached)
            return [DocumentModel.model_validate(d) for d in data]
        except Exception:
            cache_delete(cache_key)
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

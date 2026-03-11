# SPDX-License-Identifier: MIT
"""Search index management — SearchRepository, SearchIndex, project state."""

from __future__ import annotations

import atexit
import json
import logging
import os
import re
import sqlite3
import threading
from collections import Counter
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Dict, Set

from ._models import DEFAULT_PROJECT_ID, ProjectModel, SavedSearch

logger = logging.getLogger(__name__)


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
            conn.execute(
                "ALTER TABLE saved_searches ADD COLUMN flagged INTEGER NOT NULL DEFAULT 0"
            )

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

        from ..workflows import get_workflow

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
                    INSERT OR REPLACE INTO saved_searches
                    (id, query, user, created, count, flagged)
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
        import uuid

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
        if project.updated is None:
            project.updated = datetime.now(UTC)
        self.projects[project.id] = project

    def generate_project_id(self) -> str:
        """Generate a unique project ID."""
        import uuid

        return str(uuid.uuid4())

    def add_document(self, document: object) -> None:
        """Index tokens from the document and associated project."""
        import sys

        doc = document  # type: ignore[assignment]

        def _normalize(text: str) -> str:
            cleaned = re.sub(r"[^\w]+", " ", text)
            return cleaned.lower().strip()

        tokens = _normalize(doc.content).split()  # type: ignore[union-attr]
        if doc.project and doc.project in self.projects:  # type: ignore[union-attr]
            tokens += _normalize(self.projects[doc.project].name).split()
        # Use sys.modules to avoid a circular import with search/__init__.py
        pkg = sys.modules.get(__name__.rpartition(".")[0])
        lock = getattr(pkg, "index_lock", None) if pkg is not None else None
        if lock is not None:
            with lock:
                for token in tokens:
                    self.index.setdefault(token, set()).add(doc.id)  # type: ignore[union-attr]
        else:
            for token in tokens:
                self.index.setdefault(token, set()).add(doc.id)  # type: ignore[union-attr]

    def remove_document(self, doc_id: str) -> None:
        """Remove a document from the index."""
        import sys

        pkg = sys.modules.get(__name__.rpartition(".")[0])
        lock = getattr(pkg, "index_lock", None) if pkg is not None else None
        if lock is not None:
            with lock:
                for ids in self.index.values():
                    ids.discard(doc_id)
        else:
            for ids in self.index.values():
                ids.discard(doc_id)

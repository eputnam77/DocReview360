# SPDX-License-Identifier: MIT
"""Project service — business logic wrapper around project CRUD operations."""

from __future__ import annotations

import logging
from typing import Optional

from ..search._models import ProjectModel

_logger = logging.getLogger(__name__)


class ProjectService:
    """Thin service layer for project lifecycle operations.

    Centralises logic that previously lived inline in route handlers so that it
    can be unit-tested without an HTTP layer and reused across multiple routers.
    """

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get(self, project_id: str) -> Optional[ProjectModel]:
        """Return a project by ID or ``None`` if it does not exist."""
        from ..search import get_project

        return get_project(project_id)

    def list(self, user: Optional[str] = None) -> list[ProjectModel]:
        """Return projects, optionally filtered by assigned user."""
        from ..search import list_projects

        return list_projects(user)

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def set_priority(self, project_id: str, priority: int) -> ProjectModel:
        """Update the priority of an existing project."""
        from ..search import set_project_priority

        _logger.info("Setting project %s priority to %d", project_id, priority)
        return set_project_priority(project_id, priority)

    def update_reviewer(
        self, project_id: str, current_reviewer: str, new_reviewer: str
    ) -> ProjectModel:
        """Reassign a project from one reviewer to another."""
        from ..search import update_project_reviewer

        _logger.info(
            "Updating reviewer for project %s: %s -> %s",
            project_id,
            current_reviewer,
            new_reviewer,
        )
        return update_project_reviewer(project_id, current_reviewer, new_reviewer)

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def assert_exists(self, project_id: str) -> ProjectModel:
        """Return the project or raise ``KeyError`` if it does not exist."""
        project = self.get(project_id)
        if project is None:
            raise KeyError(f"Project not found: {project_id}")
        return project

    def user_can_view(self, project: ProjectModel, username: str) -> bool:
        """Return ``True`` when *username* is allowed to view *project*."""
        return project.user == username or project.temp_user == username

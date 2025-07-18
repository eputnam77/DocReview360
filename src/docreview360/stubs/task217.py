"""Project Lead field helper (Task 217)."""

from __future__ import annotations

from ..search import ProjectModel
from . import record_task_completion


def apply_default_lead(project: ProjectModel, current_user: str) -> ProjectModel:
    """Set ``project.user`` to ``current_user`` if empty and return project."""
    if not current_user:
        raise ValueError("current_user required")
    record_task_completion(217)
    if project.user is None:
        project.user = current_user
    return project

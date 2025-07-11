"""AI-validated project creation helpers (task 35)."""

from __future__ import annotations

from typing import Iterable

from .ai_utils import validate_content
from .search import ProjectModel, add_project
from .workflows import assign_reviewer, create_workflow


def create_project_with_validation(
    project_id: str,
    name: str,
    description: str,
    reviewers: Iterable[str] | None = None,
) -> tuple[ProjectModel, str]:
    """Create a project and workflow after validating ``description``."""
    if not validate_content(description):
        raise ValueError("Description failed validation")
    project = ProjectModel(id=project_id, name=name)
    add_project(project)
    workflow = create_workflow(project_id, ["draft", "review", "done"])
    for user in reviewers or []:
        assign_reviewer(workflow.id, user)
    return project, workflow.id

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel

from .documents import DocumentModel, documents


class ProjectModel(BaseModel):
    """Representation of a project with assignment metadata."""

    id: str
    name: str
    user: Optional[str] = None
    priority: int = 0
    created: datetime = datetime.utcnow()
    temp_user: Optional[str] = None
    temp_until: datetime | None = None


projects: Dict[str, ProjectModel] = {"1": ProjectModel(id="1", name="Example")}


def add_project(project: ProjectModel) -> None:
    """Store a project in memory."""
    projects[project.id] = project


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


def assign_temporary(project_id: str, user: str, until: datetime) -> ProjectModel:
    """Temporarily assign a project to another user."""
    project = projects[project_id]
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

    normalized = query.lower()
    results: List[DocumentModel] = []

    for doc in documents.values():
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

        project_obj = projects.get(doc.project) if doc.project else None
        if normalized in doc.content.lower() or (
            project_obj and normalized in project_obj.name.lower()
        ):
            results.append(doc)

    return results

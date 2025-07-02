from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel

from .documents import DocumentModel, documents


class ProjectModel(BaseModel):
    """Minimal project representation for search filtering."""

    id: str
    name: str
    user: Optional[str] = None
    priority: Optional[int] = None
    created: datetime = datetime.utcnow()


projects: Dict[str, ProjectModel] = {"1": ProjectModel(id="1", name="Example")}


def add_project(project: ProjectModel) -> None:
    """Store a project in memory."""
    projects[project.id] = project


def list_projects() -> list[ProjectModel]:
    """Return all projects."""
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

"""Implementation for task 166."""

from ..search import ProjectModel, add_project, list_projects
from ..stubs import record_task_completion


def task166() -> bool:
    """Verify user filtering for projects."""
    record_task_completion(166)
    proj = ProjectModel(id="u1", name="Scoped", user="alice")
    add_project(proj)
    filtered = list_projects(user="alice")
    return proj in filtered and all(p.user == "alice" for p in filtered)

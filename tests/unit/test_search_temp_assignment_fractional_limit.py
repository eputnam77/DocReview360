from datetime import UTC, datetime, timedelta

import pytest
from docreview360.search import (
    TEMP_ASSIGN_MAX_DAYS,
    ProjectModel,
    assign_temporary,
    project_lock,
    projects,
    search_index,
)


def test_assign_temporary_requires_approval_for_fractional_over_limit() -> None:
    """Assignments slightly beyond the limit should require manager approval."""

    with project_lock:
        projects.clear()
        search_index.projects.clear()

    project = ProjectModel(id="p1", name="Project")
    search_index.add_project(project)

    until = datetime.now(UTC) + timedelta(days=TEMP_ASSIGN_MAX_DAYS, minutes=1)

    with pytest.raises(ValueError):
        assign_temporary("p1", "temp", until, approved=False)

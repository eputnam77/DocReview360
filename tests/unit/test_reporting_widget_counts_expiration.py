from datetime import UTC, datetime, timedelta

from docreview360.search import ProjectModel, projects
from docreview360.reporting import widget_counts


def test_widget_counts_expires_temp_assignments():
    projects.clear()
    proj = ProjectModel(
        id="p1",
        name="Proj",
        temp_user="alice",
        temp_until=datetime.now(UTC) - timedelta(days=1),
    )
    projects[proj.id] = proj
    counts = widget_counts()
    assert counts["assigned"] == 0
    assert counts["active"] == 0
    projects.clear()

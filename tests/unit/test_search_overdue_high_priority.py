"""Ensure overdue high-priority detection handles naive timestamps."""

from __future__ import annotations

from datetime import datetime, timedelta

from docreview360 import search


def test_overdue_high_priority_handles_naive_created() -> None:
    """Naive created timestamps should be treated as UTC."""
    created = datetime.utcnow() - timedelta(days=20)
    project = search.ProjectModel(id="late", name="Late Project", priority=5, created=created)
    original = search.projects.copy()
    try:
        search.projects[project.id] = project
        overdue = search.overdue_high_priority()
        assert project.id in overdue
    finally:
        search.projects.clear()
        search.projects.update(original)

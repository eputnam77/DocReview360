import pytest
from docreview360 import search, workflows
from docreview360.project_init import create_project_with_validation


def test_create_project_with_validation() -> None:
    search.projects.clear()
    workflows.workflows.clear()
    proj, wf_id = create_project_with_validation("p1", "Test", "Good desc", ["ann"])
    assert proj.id in search.projects
    assert workflows.workflows[wf_id].reviewers == ["ann"]


def test_create_project_invalid() -> None:
    with pytest.raises(ValueError):
        create_project_with_validation("p2", "Bad", "", [])

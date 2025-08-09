import pytest

from docreview360.search import projects
from docreview360.stubs.task151 import task151
from docreview360.workflows import get_workflow


def test_task151_completed() -> None:
    project_id, wf_id = task151()
    assert project_id in projects
    assert get_workflow(wf_id) is not None


def test_task151_invalid_doc_type() -> None:
    with pytest.raises(ValueError):
        task151(doc_type="missing")

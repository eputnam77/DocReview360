"""Workflow state machine tests."""

import pytest
from docreview360.workflows import advance_workflow, create_workflow


def test_editor_to_review_transition_only() -> None:
    wf = create_workflow("p1", ["editor", "review"])
    assert wf.phase == "editor"
    advance_workflow(wf.id)
    assert wf.phase == "review"

    wf.phase = "invalid"
    with pytest.raises(KeyError):
        advance_workflow(wf.id)

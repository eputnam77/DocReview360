import docreview360.workflow_designer as wd
from docreview360.workflows import WorkflowModel, workflows


def test_clone_workflow_allows_empty_reviewers(monkeypatch):
    workflows.clear()
    original = WorkflowModel(
        id="wf1",
        project="p",
        phase="start",
        phases=["start"],
        reviewers=["r1"],
        template="t",
        approval_steps=[],
    )
    workflows[original.id] = original
    clone = wd.clone_workflow(original.id, reviewers=[])
    assert clone.reviewers == []

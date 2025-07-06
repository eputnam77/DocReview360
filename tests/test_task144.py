from docuflow.stubs.task144 import task144
from docuflow.workflows import create_workflow, workflows


def test_task144_completed() -> None:
    wf = create_workflow("p", ["draft", "review"])
    task144(wf.id)
    assert len(workflows) >= 2

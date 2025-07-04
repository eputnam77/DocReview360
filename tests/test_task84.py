from docuflow.stubs.task84 import WorkflowEditor


def test_editor_add_node() -> None:
    ed = WorkflowEditor()
    ed.add_node("n1", {"type": "start"})
    assert ed.node_ids() == ["n1"]

from docreview360.stubs.task84 import WorkflowEditor


def test_editor_edges() -> None:
    ed = WorkflowEditor()
    ed.add_node("n1", {"type": "start"})
    ed.add_node("n2", {"type": "end"})
    ed.add_edge("n1", "n2")
    assert ed.node_ids() == ["n1", "n2"]
    assert ed.edges_list() == [("n1", "n2")]

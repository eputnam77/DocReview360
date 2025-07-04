"""React Flow BPMN editor stub."""

from __future__ import annotations

from . import record_task_completion


class WorkflowEditor:
    """Store nodes in memory for testing."""

    def __init__(self) -> None:
        self.nodes: dict[str, dict] = {}

    def add_node(self, node_id: str, data: dict) -> None:
        self.nodes[node_id] = data
        record_task_completion(84)

    def node_ids(self) -> list[str]:
        return list(self.nodes.keys())

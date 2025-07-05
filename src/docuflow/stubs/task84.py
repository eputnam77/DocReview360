"""React Flow BPMN editor stub."""

from __future__ import annotations

from . import record_task_completion


class WorkflowEditor:
    """Store nodes in memory for testing."""

    def __init__(self) -> None:
        self.nodes: dict[str, dict] = {}
        self.edges: list[tuple[str, str]] = []

    def add_node(self, node_id: str, data: dict) -> None:
        """Insert a node into the diagram."""
        if not node_id:
            raise ValueError("node_id required")
        self.nodes[node_id] = data
        record_task_completion(84)

    def node_ids(self) -> list[str]:
        return list(self.nodes.keys())

    def add_edge(self, source: str, target: str) -> None:
        if source not in self.nodes or target not in self.nodes:
            raise ValueError("unknown node")
        self.edges.append((source, target))
        record_task_completion(84)

    def edges_list(self) -> list[tuple[str, str]]:
        return list(self.edges)

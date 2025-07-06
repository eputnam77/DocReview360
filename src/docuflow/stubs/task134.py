"""Workflow DSL examples helper."""

from pathlib import Path

from . import record_task_completion


def task134() -> list[Path]:
    """Return example workflow files."""
    root = Path("examples/workflow")
    files = list(root.glob("*.yaml"))
    if not files:
        raise FileNotFoundError(root)
    record_task_completion(134)
    return files

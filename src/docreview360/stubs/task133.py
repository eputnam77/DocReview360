"""Security process documentation helper."""

from pathlib import Path

from . import record_task_completion


def task133() -> Path:
    """Return path to the patch-flow document."""
    # Use path relative to project root (going up 3 levels from stubs/task133.py to project root)
    project_root = Path(__file__).resolve().parents[3]
    doc = project_root / "docs" / "security" / "patch-flow.md"
    if not doc.exists():
        raise FileNotFoundError(doc)
    record_task_completion(133)
    return doc

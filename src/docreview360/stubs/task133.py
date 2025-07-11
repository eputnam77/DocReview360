"""Security process documentation helper."""

from pathlib import Path

from . import record_task_completion


def task133() -> Path:
    """Return path to the patch-flow document."""
    doc = Path("docs/security/patch-flow.md")
    if not doc.exists():
        raise FileNotFoundError(doc)
    record_task_completion(133)
    return doc

"""GitHub document storage sync helper."""

from __future__ import annotations

import tempfile
from pathlib import Path

from ..github_sync import pull_document, push_document
from ..stubs import record_task_completion


def task198(tmp: Path | None = None) -> bool:
    """Round trip a document through a git repo."""
    tmp = tmp or Path(tempfile.mkdtemp())
    repo = tmp / "repo"
    doc = tmp / "demo.txt"
    doc.write_text("hello")
    commit = push_document(doc, repo)
    result = pull_document(doc.name, repo)
    record_task_completion(198)
    return result == b"hello" and len(commit) == 40

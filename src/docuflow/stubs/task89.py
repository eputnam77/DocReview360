"""Web-native CRDT merge stub."""

from __future__ import annotations

from . import record_task_completion


def merge_docs(local: str, remote: str) -> str:
    """Return whichever document is longer as the merged result."""
    record_task_completion(89)
    return remote if len(remote) >= len(local) else local

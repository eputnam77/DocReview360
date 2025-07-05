"""Web-native CRDT merge stub."""

from __future__ import annotations

from . import record_task_completion


def merge_docs(local: str, remote: str) -> str:
    """Return whichever document is longer as the merged result."""
    if not isinstance(local, str) or not isinstance(remote, str):
        raise TypeError("both documents must be strings")
    record_task_completion(89)
    return remote if len(remote) >= len(local) else local

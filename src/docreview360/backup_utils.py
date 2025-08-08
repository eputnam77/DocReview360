"""Utilities for creating and restoring DocReview360 backups."""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any, Dict

from .documents import DocumentModel, documents
from .logs import LogEntry, logs


def create_backup(path: str | Path) -> Path:
    """Write a gzip-compressed JSON backup of documents and logs."""
    target = Path(path)

    # Use document lock to prevent race conditions during backup
    from .documents import document_lock

    with document_lock:
        data: Dict[str, Any] = {
            "documents": [doc.model_dump(mode="json") for doc in documents.values()],
            "logs": [entry.model_dump(mode="json") for entry in logs],
        }

    target.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(target, "wt", encoding="utf-8") as fh:
        json.dump(data, fh)
    return target


def restore_backup(path: str | Path) -> None:
    """Load documents and logs from a backup created by :func:`create_backup`."""
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(target)
    with gzip.open(target, "rt", encoding="utf-8") as fh:
        data = json.load(fh)

    # Use document lock to prevent race conditions during restore
    from .documents import document_lock

    with document_lock:
        documents.clear()
        for d in data.get("documents", []):
            documents[d["id"]] = DocumentModel(**d)
        logs.clear()
        for entry in data.get("logs", []):
            logs.append(LogEntry(**entry))

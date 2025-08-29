"""Utilities for creating and restoring DocReview360 backups."""

from __future__ import annotations

import base64
import binascii
import gzip
import json
from pathlib import Path
from typing import Any, Dict

from .documents import DocumentModel, documents
from .logs import LogEntry, logs


def _dump_document(doc: DocumentModel) -> Dict[str, Any]:
    """Return a JSON-serialisable representation of ``doc``.

    ``DocumentModel`` includes ``bytes`` in ``yjs_updates`` which are not
    JSON serialisable.  We encode those values using base64 so backups can be
    written without raising ``UnicodeDecodeError``.
    """

    data = doc.model_dump(mode="json", exclude={"yjs_updates"})
    yjs = getattr(doc, "yjs_updates", None)
    if yjs is not None:
        data["yjs_updates"] = [
            base64.b64encode(u).decode("ascii") for u in yjs
        ]
    return data


def create_backup(path: str | Path) -> Path:
    """Write a gzip-compressed JSON backup of documents and logs."""
    target = Path(path)

    # Use document lock to prevent race conditions during backup
    from .documents import document_lock

    with document_lock:
        data: Dict[str, Any] = {
            "documents": [_dump_document(doc) for doc in documents.values()],
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

    if not isinstance(data, dict):
        raise ValueError("backup must contain a JSON object")

    docs = data.get("documents", [])
    logs_data = data.get("logs", [])
    if not isinstance(docs, list) or not isinstance(logs_data, list):
        raise ValueError("documents and logs must be lists")

    # Use document lock to prevent race conditions during restore
    from .documents import document_lock

    # Validate and construct objects **before** mutating global state.  The
    # previous implementation cleared ``documents`` and ``logs`` up-front which
    # meant any subsequent error (for example invalid base64 in
    # ``yjs_updates``) would leave the application with an empty in-memory
    # store even though the restore failed.  Building the new structures in
    # temporary containers preserves the original state if validation fails.
    new_docs: Dict[str, DocumentModel] = {}
    for d in docs:
        if not isinstance(d, dict):
            raise ValueError("documents entries must be objects")
        if "yjs_updates" in d and d["yjs_updates"] is not None:
            updates = d["yjs_updates"]
            if not isinstance(updates, list):
                raise ValueError("yjs_updates must be a list")
            try:
                d["yjs_updates"] = [base64.b64decode(u, validate=True) for u in updates]
            except (binascii.Error, TypeError) as exc:
                raise ValueError("Invalid base64 in yjs_updates") from exc
        new_docs[d["id"]] = DocumentModel(**d)

    new_logs = [LogEntry(**entry) for entry in logs_data]

    with document_lock:
        documents.clear()
        documents.update(new_docs)
        logs.clear()
        logs.extend(new_logs)

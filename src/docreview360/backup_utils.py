# SPDX-License-Identifier: MIT
"""Utilities for creating and restoring DocReview360 backups."""

from __future__ import annotations

import base64
import binascii
import gzip
import json
from pathlib import Path
from typing import Any, Dict

from .crypto import (
    decrypt_payload,
    encrypt_payload,
    enforce_encryption_choice,
    get_encryption_policy,
)
from .documents import DocumentModel, documents
from .logs import LogEntry, logs
from .settings_manager import load_settings


def _dump_document(doc: DocumentModel) -> Dict[str, Any]:
    """Return a JSON-serialisable representation of ``doc``.

    ``DocumentModel`` includes ``bytes`` in ``yjs_updates`` which are not
    JSON serialisable.  We encode those values using base64 so backups can be
    written without raising ``UnicodeDecodeError``.
    """

    data = doc.model_dump(mode="json", exclude={"yjs_updates"})
    yjs = getattr(doc, "yjs_updates", None)
    if yjs is not None:
        data["yjs_updates"] = [base64.b64encode(u).decode("ascii") for u in yjs]
    return data


def create_backup(path: str | Path, *, encrypt: bool | None = None) -> Path:
    """Write a gzip-compressed JSON backup of documents and logs."""
    target = Path(path)

    # Use document lock to prevent race conditions during backup
    from .documents import document_lock

    with document_lock:
        data: Dict[str, Any] = {
            "documents": [_dump_document(doc) for doc in documents.values()],
            "logs": [entry.model_dump(mode="json") for entry in logs],
        }

    payload = json.dumps(data).encode("utf-8")
    compressed = gzip.compress(payload)
    settings = load_settings()
    policy = get_encryption_policy(settings)
    if encrypt is None:
        encrypt = policy.enabled
    enforce_encryption_choice(scope="backup", encrypt=encrypt, settings=settings)
    blob = (
        encrypt_payload(compressed, settings=settings)
        if encrypt
        else compressed
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(blob)
    return target


def _parse_document(d: Any) -> DocumentModel:
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
    return DocumentModel(**d)


def _parse_log(entry: Any) -> LogEntry:
    if not isinstance(entry, dict):
        raise ValueError("log entries must be objects")
    return LogEntry(**entry)


def restore_backup(path: str | Path) -> None:
    """Load documents and logs from a backup created by :func:`create_backup`."""
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(target)
    settings = load_settings()
    try:
        raw = target.read_bytes()
        try:
            decrypted = decrypt_payload(raw, settings=settings, allow_plaintext=True)
        except Exception as exc:
            raise ValueError(f"backup decryption failed: {exc}") from exc
        try:
            decompressed = gzip.decompress(decrypted)
        except OSError as exc:
            raise ValueError("backup must be a valid gzip file") from exc
        try:
            data = json.loads(decompressed.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            # ``restore_backup`` previously leaked ``JSONDecodeError`` or
            # ``UnicodeDecodeError`` when the gzipped file contained malformed
            # or non-UTF-8 JSON.  Callers expect a generic :class:`ValueError`
            # for any format issues, mirroring the checks below for incorrect
            # data types.  Re-wrap the exception so clients receive a consistent
            # error surface regardless of where parsing failed.
            raise ValueError("backup must contain valid JSON") from exc
    except OSError as exc:
        # ``gzip.open`` or ``json.load`` may raise ``OSError`` when the file is
        # not actually a gzip archive.  Present a uniform ``ValueError`` so
        # callers don't have to special-case the underlying compression layer.
        raise ValueError("backup must be a valid gzip file") from exc

    if not isinstance(data, dict):
        raise ValueError("backup must contain a JSON object")

    docs = data.get("documents", [])
    logs_data = data.get("logs", [])
    if not isinstance(docs, list) or not isinstance(logs_data, list):
        raise ValueError("documents and logs must be lists")

    # Use document lock to prevent race conditions during restore
    from .documents import document_lock

    parsed_docs = [_parse_document(d) for d in docs]
    ids = [doc.id for doc in parsed_docs]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate document ids in backup")
    new_docs = {doc.id: doc for doc in parsed_docs}
    new_logs = [_parse_log(e) for e in logs_data]

    with document_lock:
        documents.clear()
        documents.update(new_docs)
        logs.clear()
        logs.extend(new_logs)

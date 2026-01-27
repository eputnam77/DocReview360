"""Export and import complete instance data for migrations."""

from __future__ import annotations

import base64
import binascii
import gzip
import json
from pathlib import Path

from . import doc_types
from .backup_utils import create_backup, restore_backup


def export_instance(path: str | Path) -> Path:
    """Write a gzip archive containing documents, logs and document types."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    tmp = target.with_suffix(".tmp")
    create_backup(tmp)
    doc_type_file = target.with_suffix(".types.json")
    doc_types.export_document_types(doc_type_file)

    data = {
        "backup": base64.b64encode(tmp.read_bytes()).decode(),
        "doc_types": json.loads(doc_type_file.read_text()),
    }
    with gzip.open(target, "wt", encoding="utf-8") as fh:
        json.dump(data, fh)

    tmp.unlink(missing_ok=True)
    doc_type_file.unlink(missing_ok=True)
    return target


def import_instance(path: str | Path) -> None:
    """Load instance data from ``path`` created by :func:`export_instance`."""
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(target)
    try:
        with gzip.open(target, "rt", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("migration archive must be a valid gzip JSON file") from exc

    if not isinstance(data, dict):
        raise ValueError("migration archive must contain an object")

    if "backup" not in data:
        raise ValueError("migration archive missing backup payload")
    if "doc_types" not in data:
        raise ValueError("migration archive missing doc_types payload")

    backup_payload = data["backup"]
    if not isinstance(backup_payload, str) or not backup_payload.strip():
        raise ValueError("migration archive backup must be a base64 string")
    try:
        backup_bytes = base64.b64decode(backup_payload, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("migration archive backup must be base64-encoded") from exc

    types = data["doc_types"]
    if not isinstance(types, list):
        raise ValueError("migration archive doc_types must be a list")

    tmp = target.with_suffix(".tmp")
    temp_json = target.with_suffix(".types.json")
    try:
        tmp.write_bytes(backup_bytes)
        restore_backup(tmp)
        temp_json.write_text(json.dumps(types))
        doc_types.import_document_types(temp_json)
    finally:
        tmp.unlink(missing_ok=True)
        temp_json.unlink(missing_ok=True)

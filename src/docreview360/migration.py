"""Export and import complete instance data for migrations."""

from __future__ import annotations

import base64
import gzip
import json
from pathlib import Path

from .backup_utils import create_backup, restore_backup
from .doc_types import export_document_types, import_document_types


def export_instance(path: str | Path) -> Path:
    """Write a gzip archive containing documents, logs and document types."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    tmp = target.with_suffix(".tmp")
    create_backup(tmp)
    doc_type_file = target.with_suffix(".types.json")
    export_document_types(doc_type_file)

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
    with gzip.open(target, "rt", encoding="utf-8") as fh:
        data = json.load(fh)
    tmp = target.with_suffix(".tmp")
    backup_bytes = base64.b64decode(data.get("backup", ""))
    tmp.write_bytes(backup_bytes)
    restore_backup(tmp)
    tmp.unlink(missing_ok=True)
    types = data.get("doc_types", [])
    temp_json = target.with_suffix(".types.json")
    temp_json.write_text(json.dumps(types))
    import_document_types(temp_json)
    temp_json.unlink(missing_ok=True)

# SPDX-License-Identifier: MIT
"""Document type registry — CRUD, import/export, default data, DB-backed view."""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Iterator, MutableMapping
from typing import Any, Dict, List

from pydantic import ValidationError
from sqlalchemy import delete, select

from ..db_store import get_db
from ..models import DocumentType as DocumentTypeORM
from ._models import DocumentTypeModel, _validate_workflow

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default data
# ---------------------------------------------------------------------------

DEFAULT_DOC_TYPE_PHASES: Dict[str, List[str]] = {
    "Advisory Circular": [
        "Draft Development",
        "Internal Coordination",
        "Final Issuance",
    ],
    "Order / Directive": [
        "Draft Development",
        "Internal Coordination",
        "Final Issuance",
    ],
    "Policy": [
        "Draft Development",
        "Internal Coordination",
        "Final Issuance",
    ],
    "Guidance": [
        "Draft Development",
        "Internal Coordination",
        "Final Issuance",
    ],
    "Memorandum": [
        "Draft Development",
        "Internal Coordination",
        "Final Issuance",
    ],
    "SOP": [
        "Draft Development",
        "Peer Review",
        "Internal Coordination",
        "Final Issuance",
    ],
    "Desk Guide": [
        "Draft Development",
        "Peer Review",
        "Internal Coordination",
        "Final Issuance",
    ],
    "Manual / Handbook": [
        "Draft Development",
        "Peer Review",
        "Internal Coordination",
        "Final Issuance",
    ],
    "Report": [
        "Draft Development",
        "Peer Review",
        "Final Issuance",
    ],
    "Audit Report": [
        "Draft Development",
        "Peer Review",
        "Internal Coordination",
        "Final Issuance",
    ],
    "After-Action Report": [
        "Draft Development",
        "Peer Review",
        "Final Issuance",
    ],
    "Briefing / Slide Deck": [
        "Draft Development",
        "Internal Coordination",
        "Final Issuance",
    ],
    "Meeting Minutes": [
        "Draft Development",
        "Internal Coordination",
        "Final Issuance",
    ],
    "Federal Register Notice": [
        "Draft Development",
        "Internal Coordination",
        "Public Comment / Proposed Rulemaking",
        "Final Issuance",
    ],
    "Proposed Rule / NPRM": [
        "Draft Development",
        "Internal Coordination",
        "Public Comment / Proposed Rulemaking",
        "Final Issuance",
    ],
    "Final Rule": [
        "Draft Development",
        "Internal Coordination",
        "Public Comment / Proposed Rulemaking",
        "Final Issuance",
    ],
    "Supporting Statement (PRA)": [
        "Draft Development",
        "Internal Coordination",
        "Public Comment / Proposed Rulemaking",
        "Final Issuance",
    ],
    "ICR": [
        "Draft Development",
        "Internal Coordination",
        "Public Comment / Proposed Rulemaking",
        "Final Issuance",
    ],
    "Exemption / Waiver": [
        "Draft Development",
        "Internal Coordination",
        "Public Comment / Proposed Rulemaking",
        "Final Issuance",
    ],
    "Special Conditions": [
        "Draft Development",
        "Internal Coordination",
        "Public Comment / Proposed Rulemaking",
        "Final Issuance",
    ],
    "FAQ": [
        "Draft Development",
        "Internal Review",
        "Publication",
    ],
    "Letter / Correspondence": [
        "Draft Development",
        "Internal Review",
        "Publication",
    ],
    "Web Content": [
        "Draft Development",
        "Internal Review",
        "Publication",
    ],
    "Release Notes": [
        "Draft Development",
        "Peer Review",
        "Release Candidate Review",
        "General Availability",
        "Maintenance / Revision Cycle",
    ],
    "User Guide": [
        "Draft Development",
        "Peer Review",
        "Release Candidate Review",
        "General Availability",
        "Maintenance / Revision Cycle",
    ],
    "API Manual / API Reference": [
        "Draft Development",
        "Peer Review",
        "Release Candidate Review",
        "General Availability",
        "Maintenance / Revision Cycle",
    ],
    "README": [
        "Draft Development",
        "Peer Review",
        "Release Candidate Review",
        "General Availability",
        "Maintenance / Revision Cycle",
    ],
}

DEFAULT_DOC_TYPE_NAMES = list(DEFAULT_DOC_TYPE_PHASES.keys())

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_explicit_clear_active: bool = False
_explicit_clear_lock = threading.Lock()
"""Guards reads and writes of ``_explicit_clear_active`` across threads."""


def _bootstrap_if_empty() -> None:
    """Seed default document types when the table is empty."""
    global _explicit_clear_active

    with _explicit_clear_lock:
        if _explicit_clear_active:
            return

    db = get_db()
    with db.session() as conn:
        from sqlalchemy import text as _text

        count = conn.execute(_text("SELECT COUNT(*) FROM document_types")).scalar()
        if count:
            return
        with _explicit_clear_lock:
            _explicit_clear_active = False
        for order, (name, phases) in enumerate(DEFAULT_DOC_TYPE_PHASES.items(), start=1):
            conn.execute(
                _text(
                    "INSERT OR IGNORE INTO document_types "
                    "(name, template, workflow, display_order) "
                    "VALUES (:name, :template, :workflow, :order)"
                ),
                {
                    "name": name,
                    "template": f"<h1>{name}</h1>",
                    "workflow": json.dumps(phases),
                    "order": order,
                },
            )


def _row_to_model(row: Any) -> DocumentTypeModel:
    """Convert a DB row (or ORM object) to :class:`DocumentTypeModel`."""
    if isinstance(row, DocumentTypeORM):
        workflow = row.workflow if isinstance(row.workflow, list) else json.loads(
            row.workflow or "[]"
        )
        return DocumentTypeModel(
            name=row.name,
            template=row.template or "",
            workflow=workflow,
            default_template_id=row.default_template_id,
        )
    name = row.name if hasattr(row, "name") else row[0]
    template = row.template if hasattr(row, "template") else (row[1] if len(row) > 1 else "")
    raw_workflow = (
        row.workflow if hasattr(row, "workflow") else (row[2] if len(row) > 2 else "[]")
    )
    workflow = raw_workflow if isinstance(raw_workflow, list) else json.loads(raw_workflow or "[]")
    default_template_id = (
        row.default_template_id
        if hasattr(row, "default_template_id")
        else (row[3] if len(row) > 3 else None)
    )
    return DocumentTypeModel(
        name=name,
        template=template or "",
        workflow=workflow,
        default_template_id=default_template_id,
    )


# ---------------------------------------------------------------------------
# CRUD operations
# ---------------------------------------------------------------------------


def add_document_type(doc_type: DocumentTypeModel | dict[str, Any]) -> DocumentTypeModel:
    """Store a document type in the database."""
    if isinstance(doc_type, dict):
        doc_type = DocumentTypeModel(**doc_type)
    else:
        doc_type = DocumentTypeModel.model_validate(doc_type.model_dump())
    _validate_workflow(doc_type)

    if not doc_type.name.strip():
        raise ValueError("Document type name must not be empty")

    from sqlalchemy import text as _text

    db = get_db()
    with db.session() as conn:
        existing = conn.execute(
            select(
                DocumentTypeORM.name,
                DocumentTypeORM.template,
                DocumentTypeORM.workflow,
                DocumentTypeORM.default_template_id,
            ).where(DocumentTypeORM.name == doc_type.name)
        ).one_or_none()

        if existing is not None:
            existing_model = _row_to_model(existing)
            if existing_model.model_dump() != doc_type.model_dump():
                raise ValueError(f"Document type '{doc_type.name}' already exists")
            return existing_model

        conn.execute(
            _text(
                "INSERT INTO document_types (name, template, workflow, default_template_id) "
                "VALUES (:name, :template, :workflow, :dtid)"
            ),
            {
                "name": doc_type.name,
                "template": doc_type.template,
                "workflow": json.dumps(doc_type.workflow),
                "dtid": doc_type.default_template_id,
            },
        )
    return doc_type


def get_document_type(name: str) -> DocumentTypeModel | None:
    """Retrieve a document type by name."""
    _bootstrap_if_empty()
    db = get_db()
    with db.session() as conn:
        row = conn.execute(
            select(
                DocumentTypeORM.name,
                DocumentTypeORM.template,
                DocumentTypeORM.workflow,
                DocumentTypeORM.default_template_id,
            ).where(DocumentTypeORM.name == name)
        ).one_or_none()
        if row is None:
            return None
        return _row_to_model(row)


def list_document_types() -> list[DocumentTypeModel]:
    """Return all known document types sorted alphabetically by name."""
    _bootstrap_if_empty()
    db = get_db()
    with db.session() as conn:
        rows = conn.execute(
            select(
                DocumentTypeORM.name,
                DocumentTypeORM.template,
                DocumentTypeORM.workflow,
                DocumentTypeORM.default_template_id,
            ).order_by(DocumentTypeORM.name)
        ).all()
        return [_row_to_model(row) for row in rows]


def update_document_type(name: str, doc_type: DocumentTypeModel) -> DocumentTypeModel:
    """Update an existing document type and persist changes."""
    existing = get_document_type(name)
    if existing is None:
        raise KeyError(f"Document type '{name}' not found")

    doc_type = DocumentTypeModel.model_validate(doc_type.model_dump())
    _validate_workflow(doc_type)

    from sqlalchemy import text as _text

    if doc_type.name != name:
        if get_document_type(doc_type.name) is not None:
            raise ValueError(f"Document type '{doc_type.name}' already exists")

        try:
            from ..search import projects

            for proj in projects.values():
                if proj.doc_type == name:
                    proj.doc_type = doc_type.name
        except Exception as exc:  # pragma: no cover - best-effort
            _logger.warning("Failed to update in-memory project doc_type on rename: %s", exc)

    db = get_db()
    with db.session() as conn:
        conn.execute(
            _text(
                "UPDATE document_types SET name=:new_name, template=:template, "
                "workflow=:workflow, default_template_id=:dtid WHERE name=:old_name"
            ),
            {
                "old_name": name,
                "new_name": doc_type.name,
                "template": doc_type.template,
                "workflow": json.dumps(doc_type.workflow),
                "dtid": doc_type.default_template_id,
            },
        )
    return doc_type


def delete_document_type(name: str) -> None:
    """Delete a document type by name."""
    db = get_db()
    with db.session() as conn:
        result = conn.execute(
            delete(DocumentTypeORM).where(DocumentTypeORM.name == name)
        )
        if result.rowcount == 0:
            raise KeyError(f"Document type '{name}' not found")


# ---------------------------------------------------------------------------
# Import / Export
# ---------------------------------------------------------------------------


def export_document_types(path: str) -> None:
    """Serialize document types to *path* as JSON."""
    from pathlib import Path

    try:
        dest = Path(path)
        if dest.is_dir():
            raise ValueError(f"Export path {dest} must be a file")
        dest.parent.mkdir(parents=True, exist_ok=True)
        json_data = [doc.model_dump() for doc in list_document_types()]
        dest.write_text(json.dumps(json_data, indent=2))
    except OSError as exc:
        raise RuntimeError(f"Failed to export document types to {path}") from exc


def import_document_types(path: str) -> None:
    """Load document types from a JSON file and persist to DB."""
    from pathlib import Path

    try:
        data = json.loads(Path(path).read_text())
    except OSError as exc:
        raise RuntimeError(f"Failed to read document types from {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}") from exc

    if not isinstance(data, list):
        raise ValueError("JSON must contain a list of document types")

    temp: dict[str, DocumentTypeModel] = {}
    for item in data:
        try:
            doc = DocumentTypeModel(**item)
            _validate_workflow(doc)
        except ValidationError as exc:
            raise ValueError(f"Invalid document type entry: {item}") from exc
        temp[doc.name] = doc

    db = get_db()
    with db.session() as conn:
        from sqlalchemy import text as _text

        conn.execute(_text("DELETE FROM document_types"))
        for doc in temp.values():
            conn.execute(
                _text(
                    "INSERT INTO document_types (name, template, workflow, default_template_id) "
                    "VALUES (:name, :template, :workflow, :dtid)"
                ),
                {
                    "name": doc.name,
                    "template": doc.template,
                    "workflow": json.dumps(doc.workflow),
                    "dtid": doc.default_template_id,
                },
            )


def export_document_types_json() -> str:
    """Return document types as a JSON string."""
    json_data = [doc.model_dump() for doc in list_document_types()]
    return json.dumps(json_data, indent=2)


def import_document_types_json(data: str) -> None:
    """Load document types from a JSON string and persist to DB."""
    try:
        payload = json.loads(data)
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid JSON payload") from exc

    if not isinstance(payload, list):
        raise ValueError("JSON must contain a list of document types")

    temp: dict[str, DocumentTypeModel] = {}
    for item in payload:
        try:
            doc = DocumentTypeModel(**item)
            _validate_workflow(doc)
        except ValidationError as exc:
            raise ValueError(f"Invalid document type entry: {item}") from exc
        temp[doc.name] = doc

    db = get_db()
    with db.session() as conn:
        from sqlalchemy import text as _text

        conn.execute(_text("DELETE FROM document_types"))
        for doc in temp.values():
            conn.execute(
                _text(
                    "INSERT INTO document_types (name, template, workflow, default_template_id) "
                    "VALUES (:name, :template, :workflow, :dtid)"
                ),
                {
                    "name": doc.name,
                    "template": doc.template,
                    "workflow": json.dumps(doc.workflow),
                    "dtid": doc.default_template_id,
                },
            )


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------


def list_all_phases() -> list[str]:
    """Return a sorted list of all unique phases across all document types."""
    phases: set[str] = set()
    for doc in list_document_types():
        for phase in doc.workflow:
            phases.add(phase)
    return sorted(phases)


def reset_document_types(seed: bool = True) -> None:
    """Clear all document types and optionally re-seed defaults."""
    global _explicit_clear_active

    from sqlalchemy import text as _text

    db = get_db()
    with db.session() as conn:
        conn.execute(_text("DELETE FROM document_types"))
        with _explicit_clear_lock:
            if seed:
                _explicit_clear_active = False
                for order, (name, phases) in enumerate(DEFAULT_DOC_TYPE_PHASES.items(), start=1):
                    conn.execute(
                        _text(
                            "INSERT INTO document_types "
                            "(name, template, workflow, display_order) "
                            "VALUES (:name, :template, :workflow, :order)"
                        ),
                        {
                            "name": name,
                            "template": f"<h1>{name}</h1>",
                            "workflow": json.dumps(phases),
                            "order": order,
                        },
                    )
            else:
                _explicit_clear_active = True


# ---------------------------------------------------------------------------
# Backward-compatible dict-like view
# ---------------------------------------------------------------------------


class _DocumentTypesView(MutableMapping):
    """A dict-like view over the database-backed document types."""

    def __getitem__(self, key: str) -> DocumentTypeModel:
        result = get_document_type(key)
        if result is None:
            raise KeyError(key)
        return result

    def __setitem__(self, key: str, value: DocumentTypeModel) -> None:
        if get_document_type(key) is not None:
            update_document_type(key, value)
        else:
            add_document_type(value)

    def __delitem__(self, key: str) -> None:
        delete_document_type(key)

    def __iter__(self) -> Iterator[str]:
        return iter(dt.name for dt in list_document_types())

    def __len__(self) -> int:
        from sqlalchemy import text as _text

        db = get_db()
        with db.session() as conn:
            result = conn.execute(
                _text("SELECT COUNT(*) FROM document_types")
            ).scalar()
            return int(result or 0)

    def clear(self) -> None:  # type: ignore[override]
        """Remove all document types from the database (without re-seeding)."""
        reset_document_types(seed=False)


# Module-level dict-like object backed by the database.
document_types: MutableMapping[str, DocumentTypeModel] = _DocumentTypesView()

# ---------------------------------------------------------------------------
# Backward-compat stubs for old file-based symbols
# ---------------------------------------------------------------------------

DATA_FILE: Any = None


def save_state() -> None:  # pragma: no cover
    """No-op kept for backward compatibility with tests."""

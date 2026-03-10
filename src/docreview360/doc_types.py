# SPDX-License-Identifier: MIT
"""Database-backed document type management.

All document type state is stored in the ``document_types`` database table.
The previous JSON-file / FileLock / optimistic-locking persistence layer has
been removed (Tier 2c).

The module-level ``document_types`` attribute is a :class:`_DocumentTypesView`
that provides a dict-like interface backed directly by the database so that
existing call-sites (tests, chat_bot, etc.) continue to work without changes.
"""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Iterator, MutableMapping
from typing import Any, Dict, List

from pydantic import BaseModel, Field, ValidationError, computed_field, field_validator
from sqlalchemy import delete, select, update

from .db_store import get_db
from .models import DocumentType as DocumentTypeORM

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic schema (kept for API compatibility)
# ---------------------------------------------------------------------------


class DocumentTypeModel(BaseModel):
    """Schema for document types with optional default template linkage."""

    name: str
    template: str
    workflow: List[str] = Field(default_factory=list)
    default_template_id: str | None = None

    @computed_field(return_type=str)
    def id(self) -> str:  # noqa: A003
        """Expose ``name`` under an ``id`` field for frontend compatibility."""
        return self.name

    @computed_field(return_type=list[str])
    def phases(self) -> list[str]:
        """Surface ``workflow`` as ``phases`` for consumers expecting that key."""
        return self.workflow


class _WorkflowPayload(BaseModel):
    """Validation shim to enforce valid workflow phase values."""

    workflow: List[str]

    @field_validator("workflow")
    @classmethod
    def ensure_non_empty(cls, value: List[str]) -> List[str]:
        if not value:
            raise ValueError("Workflow must include at least one phase")
        for phase in value:
            if not isinstance(phase, str) or not phase.strip():
                raise ValueError("Workflow phases must be non-empty strings")
        return value


def _validate_workflow(doc_type: DocumentTypeModel) -> None:
    """Raise :class:`ValidationError` if *doc_type* has invalid workflow phases."""

    try:
        _WorkflowPayload.model_validate({"workflow": doc_type.workflow})
    except ValidationError as exc:  # pragma: no cover - defensive
        raise ValidationError.from_exception_data(
            DocumentTypeModel.__name__, exc.errors()
        ) from exc


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

# Tracks whether an explicit reset with seed=False has been performed.  When
# True the lazy-bootstrap in ``_bootstrap_if_empty`` is skipped so that code
# which deliberately empties the table (e.g. tests) gets an actually empty
# result from subsequent reads.
_explicit_clear_active: bool = False
_explicit_clear_lock = threading.Lock()
"""Guards reads and writes of ``_explicit_clear_active`` across threads."""


def _bootstrap_if_empty() -> None:
    """Seed default document types when the table is empty.

    Skipped after an explicit ``reset_document_types(seed=False)`` call so that
    test code can work with an intentionally empty registry.
    """
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
        # Fresh DB — seed defaults and clear the explicit-clear flag.
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
        workflow = row.workflow if isinstance(row.workflow, list) else json.loads(row.workflow or "[]")
        return DocumentTypeModel(
            name=row.name,
            template=row.template or "",
            workflow=workflow,
            default_template_id=row.default_template_id,
        )
    # SQLAlchemy Row / named tuple
    name = row.name if hasattr(row, "name") else row[0]
    template = row.template if hasattr(row, "template") else (row[1] if len(row) > 1 else "")
    raw_workflow = row.workflow if hasattr(row, "workflow") else (row[2] if len(row) > 2 else "[]")
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

        # Propagate rename to any in-memory project references.
        try:
            from .search import projects

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

    import os
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

    # Atomic replacement: clear all then insert validated set.
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
    """Clear all document types and optionally re-seed defaults.

    Intended primarily for test use to achieve a known-clean state.
    When *seed* is ``True`` (the default) the 27 built-in document types are
    re-inserted after clearing.
    """
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
                # Signal that the table was intentionally emptied — suppress
                # lazy-bootstrap on the next read so callers get an empty result.
                _explicit_clear_active = True


# ---------------------------------------------------------------------------
# Backward-compatible dict-like view
# ---------------------------------------------------------------------------


class _DocumentTypesView(MutableMapping):
    """A dict-like view over the database-backed document types.

    Provides backward compatibility for code that accesses the module-level
    ``document_types`` mapping directly (e.g. ``doc_types.document_types.clear()``
    or ``doc_types.document_types[name]``).  All operations delegate to the DB
    so there is no in-memory caching — changes made through one process are
    immediately visible to another.
    """

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
        from sqlalchemy import func, text as _text

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
# Existing code can continue to do ``from .doc_types import document_types``
# and use it as a mapping.
document_types: MutableMapping[str, DocumentTypeModel] = _DocumentTypesView()


# ---------------------------------------------------------------------------
# Backward-compat stubs for old file-based symbols
# ---------------------------------------------------------------------------

# ``DATA_FILE`` was the path to the JSON persistence file in the old
# file-based implementation.  Tests monkeypatch this attribute to isolate
# state; we keep it as a sentinel so those monkeypatches don't raise
# AttributeError.  The DB-backed module ignores its value.
DATA_FILE: Any = None


def save_state() -> None:  # pragma: no cover
    """No-op kept for backward compatibility with tests.

    The DB-backed implementation persists all changes immediately; there is
    no separate save step required.
    """

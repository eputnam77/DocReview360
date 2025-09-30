"""In-memory + persisted document type management with default bootstrapping.

When document type persistence is disabled via
``DOCREVIEW360_ENABLE_DOC_TYPE_PERSISTENCE``, this module emits a runtime
warning to make it clear that any customization happens in-memory only and will
not survive a restart.
"""

from __future__ import annotations

import json
import os
import tempfile
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from filelock import FileLock
from pydantic import BaseModel, Field, ValidationError, computed_field, field_validator

# Path to store persistent data
DATA_FILE = Path("document_types.json")


def _env_flag_enabled(value: str | None) -> bool:
    """Interpret truthy string values for the persistence feature flag."""

    if value is None:
        return True
    normalized = value.strip().lower()
    return normalized not in {"0", "false", "no", "off"}


DOCREVIEW360_ENABLE_DOC_TYPE_PERSISTENCE = _env_flag_enabled(
    os.getenv("DOCREVIEW360_ENABLE_DOC_TYPE_PERSISTENCE")
)

if not DOCREVIEW360_ENABLE_DOC_TYPE_PERSISTENCE:
    warnings.warn(
        "Document type persistence is disabled; customizations will not be saved.",
        RuntimeWarning,
        stacklevel=2,
    )


class DocumentTypeModel(BaseModel):
    """Schema for document types with optional default template linkage."""

    name: str
    template: str
    workflow: List[str] = Field(default_factory=list)
    default_template_id: str | None = None

    @computed_field(return_type=str)
    def id(self) -> str:
        """Expose ``name`` under an ``id`` field for frontend compatibility."""
        return self.name

    @computed_field(return_type=list[str])
    def phases(self) -> list[str]:
        """Surface ``workflow`` as ``phases`` for consumers expecting that key."""
        return self.workflow


class _WorkflowPayload(BaseModel):
    """Validation shim to enforce non-empty workflow definitions."""

    workflow: List[str]

    @field_validator("workflow")
    @classmethod
    def ensure_non_empty(cls, value: List[str]) -> List[str]:
        if not value:
            raise ValueError("Document types must include at least one workflow phase")
        return value


def _validate_workflow(doc_type: DocumentTypeModel) -> None:
    """Raise :class:`ValidationError` if ``doc_type`` lacks workflow phases."""

    try:
        _WorkflowPayload.model_validate({"workflow": doc_type.workflow})
    except ValidationError as exc:  # pragma: no cover - defensive
        raise ValidationError.from_exception_data(
            DocumentTypeModel.__name__, exc.errors()
        ) from exc


# In-memory store
document_types: Dict[str, DocumentTypeModel] = {}

# Track persisted version metadata for optimistic locking
_STATE_VERSION: int = 0
_STATE_UPDATED_AT: str | None = None


class StaleStateError(RuntimeError):
    """Raised when attempting to persist stale in-memory document type data."""

# Default phases per document type
DEFAULT_DOC_TYPE_PHASES: Dict[str, List[str]] = {
    "Advisory Circular": [
        "Draft Development",
        "Final Issuance",
        "Internal Coordination",
        "Public Comment / Proposed Rulemaking",
    ],
    "API Guide": [
        "Draft Development",
        "Peer Review",
        "Beta Documentation Review",
        "Release Candidate Review",
        "General Availability",
        "Maintenance / Revision Cycle",
    ],
    "CLI Guide": [
        "Draft Development",
        "Peer Review",
        "Beta Documentation Review",
        "Release Candidate Review",
        "General Availability",
        "Maintenance / Revision Cycle",
    ],
    "Deviation Memorandum": [
        "Draft Development",
        "Final Issuance",
        "Internal Coordination",
    ],
    "Exemption": [
        "Draft Development",
        "Final Issuance",
        "Internal Coordination",
        "Public Comment / Proposed Rulemaking",
    ],
    "Federal Register Notice": [
        "Draft Development",
        "Final Issuance",
        "Internal Coordination",
        "Public Comment / Proposed Rulemaking",
    ],
    "General Memorandum": [
        "Draft Development",
        "Final Issuance",
        "Internal Coordination",
    ],
    "Manual": [
        "Draft Development",
        "Peer Review",
        "Internal Coordination",
        "Beta Documentation Review",
        "Release Candidate Review",
        "General Availability",
        "Maintenance / Revision Cycle",
    ],
    "Order": [
        "Draft Development",
        "Final Issuance",
        "Internal Coordination",
        "Public Comment / Proposed Rulemaking",
    ],
    "Policy Memorandum": [
        "Draft Development",
        "Final Issuance",
        "Internal Coordination",
    ],
    "Policy Statement": [
        "Draft Development",
        "Final Issuance",
        "Internal Coordination",
        "Public Comment / Proposed Rulemaking",
    ],
    "Release Notes": [
        "Draft Development",
        "Peer Review",
        "Beta Documentation Review",
        "Release Candidate Review",
        "General Availability",
        "Maintenance / Revision Cycle",
    ],
    "Rulemaking": [
        "Draft Development",
        "Internal Coordination",
        "Public Comment / Proposed Rulemaking",
        "Final Issuance",
    ],
    "Special Class Airworthiness Criteria": [
        "Draft Development",
        "Internal Coordination",
        "Public Comment / Proposed Rulemaking",
        "Final Issuance",
    ],
    "Special Conditions": [
        "Draft Development",
        "Final Issuance",
        "Internal Coordination",
        "Public Comment / Proposed Rulemaking",
    ],
    "Standard Operating Procedure": [
        "Draft Development",
        "Peer Review",
        "Internal Coordination",
        "Beta Documentation Review",
        "Release Candidate Review",
        "General Availability",
        "Maintenance / Revision Cycle",
    ],
    "Technical Standard Order": [
        "Draft Development",
        "Final Issuance",
        "Internal Coordination",
        "Public Comment / Proposed Rulemaking",
    ],
    "White Paper": [
        "Draft Development",
        "Peer Review",
        "Internal Coordination",
        "Final Issuance",
    ],
}

# Export default document type names for consumers and tests
DEFAULT_DOC_TYPE_NAMES = list(DEFAULT_DOC_TYPE_PHASES.keys())


# --------------------------
# Persistence helpers
# --------------------------


def _state_lock() -> FileLock:
    """Return a file-based lock guarding state persistence."""

    return FileLock(str(DATA_FILE) + ".lock")


def _atomic_write(path: Path, data: str) -> None:
    """Write ``data`` to ``path`` atomically using a temporary file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as tmp_file:
        tmp_file.write(data)
        tmp_name = tmp_file.name
    os.replace(tmp_name, path)


def _load_persisted_payload() -> Tuple[list[dict[str, Any]], int, str | None, bool]:
    """Return persisted document types, version, timestamp and file presence."""

    exists = DATA_FILE.exists()
    if not exists:
        return [], 0, None, False
    try:
        payload = json.loads(DATA_FILE.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Failed to read document types from {DATA_FILE}") from exc

    if isinstance(payload, list):
        return payload, 0, None, True
    if not isinstance(payload, dict):
        raise ValueError("Saved document types must be a list or mapping")

    if "document_types" not in payload:
        raise ValueError("Saved document types mapping must include 'document_types'")

    document_payload = payload["document_types"]
    if not isinstance(document_payload, list):
        raise ValueError("Saved document types mapping must include a list under 'document_types'")

    version = payload.get("version")
    if not isinstance(version, int):
        raise ValueError("Saved document types version must be an integer")

    updated_at = payload.get("updated_at")
    if updated_at is not None and not isinstance(updated_at, str):
        raise ValueError("Saved document types updated_at must be a string when provided")

    return document_payload, version, updated_at, True


def save_state(expected_version: int | None = None) -> None:
    """Persist document_types to disk with optimistic locking."""

    global _STATE_VERSION, _STATE_UPDATED_AT

    documents = [doc.model_dump() for doc in document_types.values()]
    if expected_version is None:
        expected_version = _STATE_VERSION

    timestamp = datetime.now(timezone.utc).isoformat()

    with _state_lock():
        _, current_version, _, _ = _load_persisted_payload()
        file_version = current_version

        if file_version != expected_version:
            raise StaleStateError(
                "Document types changed on disk while attempting to save. "
                "Reload the state before retrying the save."
            )

        new_version = file_version + 1
        payload = {
            "version": new_version,
            "updated_at": timestamp,
            "document_types": documents,
        }

        try:
            serialized = json.dumps(payload, indent=2)
        except (TypeError, ValueError) as exc:
            raise RuntimeError("Failed to serialize document types for persistence") from exc

        try:
            _atomic_write(DATA_FILE, serialized)
        except OSError as exc:
            raise RuntimeError(f"Failed to save document types to {DATA_FILE}") from exc

        _STATE_VERSION = new_version
        _STATE_UPDATED_AT = timestamp


def load_state() -> bool:
    """Load document_types from disk. Returns True if loaded, False if file missing."""

    global _STATE_VERSION, _STATE_UPDATED_AT

    with _state_lock():
        try:
            payload, version, updated_at, exists = _load_persisted_payload()
        except RuntimeError:
            raise
        except ValueError as exc:
            raise ValueError("Invalid document types data on disk") from exc

    if not exists:
        _STATE_VERSION = 0
        _STATE_UPDATED_AT = None
        return False

    document_types.clear()
    for item in payload:
        try:
            doc = DocumentTypeModel(**item)
            _validate_workflow(doc)
        except ValidationError as exc:
            raise ValueError(f"Invalid document type entry in saved file: {item}") from exc
        document_types[doc.name] = doc

    _STATE_VERSION = version
    _STATE_UPDATED_AT = updated_at
    return True


# --------------------------
# Bootstrapping
# --------------------------


def _bootstrap_sample() -> None:
    """Create default document types with predefined phases if none exist."""
    if not document_types:
        for name, phases in DEFAULT_DOC_TYPE_PHASES.items():
            document_types[name] = DocumentTypeModel(
                name=name,
                template=f"<h1>{name}</h1>",
                workflow=phases,
            )


# Load from disk or bootstrap
if DOCREVIEW360_ENABLE_DOC_TYPE_PERSISTENCE and load_state():
    pass
else:
    _bootstrap_sample()
    if DOCREVIEW360_ENABLE_DOC_TYPE_PERSISTENCE:
        save_state()


# --------------------------
# CRUD Operations
# --------------------------


def add_document_type(doc_type: DocumentTypeModel | dict[str, Any]) -> DocumentTypeModel:
    """Store a document type in memory and persist it."""
    expected_version = _STATE_VERSION
    if isinstance(doc_type, dict):
        doc_type = DocumentTypeModel(**doc_type)
    else:
        doc_type = DocumentTypeModel.model_validate(doc_type.model_dump())
    _validate_workflow(doc_type)
    # Avoid accidental overwrites; callers should use ``update_document_type``
    # when modifying existing entries.  Previously ``add_document_type`` would
    # silently replace an existing document type which caused confusing test
    # failures where a duplicate definition clobbered the original.
    if not doc_type.name.strip():
        raise ValueError("Document type name must not be empty")
    if doc_type.name in document_types:
        # Adding the exact same document type multiple times should be
        # idempotent.  Several tests seed a "Test Doc" type and expect calls
        # that repeat that seed not to fail.  The previous implementation
        # always raised ``ValueError`` which made subsequent identical inserts
        # blow up even though no data would actually change.  We now treat an
        # identical re-add as a no-op while still erroring on conflicting
        # definitions to guard against accidental overwrites.
        existing = document_types[doc_type.name]
        if existing.model_dump() != doc_type.model_dump():
            raise ValueError(f"Document type '{doc_type.name}' already exists")
        return existing
    previous_state = dict(document_types)
    document_types[doc_type.name] = doc_type
    if DOCREVIEW360_ENABLE_DOC_TYPE_PERSISTENCE:
        try:
            save_state(expected_version=expected_version)
        except Exception:
            document_types.clear()
            document_types.update(previous_state)
            raise
    return doc_type


def get_document_type(name: str) -> DocumentTypeModel | None:
    """Retrieve a document type by name."""
    return document_types.get(name)


def list_document_types() -> list[DocumentTypeModel]:
    """Return all known document types."""
    return list(document_types.values())


def update_document_type(name: str, doc_type: DocumentTypeModel) -> DocumentTypeModel:
    """Update an existing document type and persist changes."""
    if name not in document_types:
        raise KeyError(f"Document type '{name}' not found")

    expected_version = _STATE_VERSION
    previous_state = dict(document_types)

    doc_type = DocumentTypeModel.model_validate(doc_type.model_dump())
    _validate_workflow(doc_type)

    # If the document type is renamed, propagate that change to any projects that
    # reference the old name.  Tests create a project, rename the document type
    # and expect the project's ``doc_type`` field to follow the rename.  The
    # original implementation simply replaced the entry in ``document_types`` and
    # left existing projects stale.
    if doc_type.name != name:
        # Prevent accidental overwrites when renaming to an already existing
        # document type. Previously the code unconditionally removed the old
        # entry and inserted the new one, clobbering any existing type with the
        # same name.  This surfaced in tests expecting a 409 Conflict when
        # attempting to rename to an existing name.
        if doc_type.name in document_types:
            raise ValueError(f"Document type '{doc_type.name}' already exists")

        from .search import projects  # Local import to avoid circular dependency

        for proj in projects.values():
            if proj.doc_type == name:
                proj.doc_type = doc_type.name

        # Remove the old key when renaming to keep ``document_types`` consistent
        del document_types[name]
        document_types[doc_type.name] = doc_type
    else:
        document_types[name] = doc_type

    if DOCREVIEW360_ENABLE_DOC_TYPE_PERSISTENCE:
        try:
            save_state(expected_version=expected_version)
        except Exception:
            document_types.clear()
            document_types.update(previous_state)
            raise
    return doc_type


def delete_document_type(name: str) -> None:
    """Delete a document type by name and persist changes."""
    expected_version = _STATE_VERSION
    previous_state = dict(document_types)
    try:
        del document_types[name]
        if DOCREVIEW360_ENABLE_DOC_TYPE_PERSISTENCE:
            try:
                save_state(expected_version=expected_version)
            except Exception:
                document_types.clear()
                document_types.update(previous_state)
                raise
    except KeyError as exc:
        raise KeyError(f"Document type '{name}' not found") from exc


# --------------------------
# Import / Export
# --------------------------


def export_document_types(path: str | Path) -> None:
    """Serialize document types to ``path`` as JSON."""
    try:
        dest = Path(path)
        if dest.is_dir():
            raise ValueError(f"Export path {dest} must be a file")
        json_data = [doc.model_dump() for doc in document_types.values()]
        dest.write_text(json.dumps(json_data, indent=2))
    except OSError as exc:
        raise RuntimeError(f"Failed to export document types to {path}") from exc


def import_document_types(path: str | Path) -> None:
    """Load document types from a JSON file and persist."""
    expected_version = _STATE_VERSION
    previous_state = dict(document_types)
    try:
        data = json.loads(Path(path).read_text())
    except OSError as exc:
        raise RuntimeError(f"Failed to read document types from {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}") from exc

    if not isinstance(data, list):
        raise ValueError("JSON must contain a list of document types")

    # Build a temporary mapping first so a validation error does not leave the
    # global ``document_types`` in a partially updated state.  The previous
    # implementation cleared the existing entries before validating the payload,
    # meaning a single bad item could wipe the in-memory registry while still
    # raising an exception.  By validating into ``temp`` we ensure atomic
    # replacement only when the input is entirely valid.
    temp: dict[str, DocumentTypeModel] = {}
    for item in data:
        try:
            doc = DocumentTypeModel(**item)
            _validate_workflow(doc)
        except ValidationError as exc:
            raise ValueError(f"Invalid document type entry: {item}") from exc
        temp[doc.name] = doc
    document_types.clear()
    document_types.update(temp)
    if DOCREVIEW360_ENABLE_DOC_TYPE_PERSISTENCE:
        try:
            save_state(expected_version=expected_version)
        except Exception:
            document_types.clear()
            document_types.update(previous_state)
            raise


def export_document_types_json() -> str:
    """Return document types as a JSON string."""
    json_data = [doc.model_dump() for doc in document_types.values()]
    return json.dumps(json_data, indent=2)


def import_document_types_json(data: str) -> None:
    """Load document types from a JSON string and persist."""
    expected_version = _STATE_VERSION
    previous_state = dict(document_types)
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
    document_types.clear()
    document_types.update(temp)
    if DOCREVIEW360_ENABLE_DOC_TYPE_PERSISTENCE:
        try:
            save_state(expected_version=expected_version)
        except Exception:
            document_types.clear()
            document_types.update(previous_state)
            raise


# --------------------------
# Utility
# --------------------------


def list_all_phases() -> list[str]:
    """Return a sorted list of all unique phases across all document types."""
    phases = set()
    for doc in document_types.values():
        for phase in doc.workflow:
            phases.add(phase)
    return sorted(phases)

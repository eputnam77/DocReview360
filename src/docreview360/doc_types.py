"""In-memory + persisted document type management with default bootstrapping."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from pydantic import BaseModel, Field, ValidationError, computed_field

# Path to store persistent data
DATA_FILE = Path("document_types.json")


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


# In-memory store
document_types: Dict[str, DocumentTypeModel] = {}

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

def save_state() -> None:
    """Persist document_types to disk."""
    try:
        json_data = [doc.model_dump() for doc in document_types.values()]
        DATA_FILE.write_text(json.dumps(json_data, indent=2))
    except OSError as exc:
        raise RuntimeError(f"Failed to save document types to {DATA_FILE}") from exc


def load_state() -> bool:
    """Load document_types from disk. Returns True if loaded, False if file missing."""
    if not DATA_FILE.exists():
        return False
    try:
        data = json.loads(DATA_FILE.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Failed to read document types from {DATA_FILE}") from exc

    if not isinstance(data, list):
        raise ValueError("Saved document types must be a list")

    document_types.clear()
    for item in data:
        try:
            doc = DocumentTypeModel(**item)
        except ValidationError as exc:
            raise ValueError(f"Invalid document type entry in saved file: {item}") from exc
        document_types[doc.name] = doc
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
if not load_state():
    _bootstrap_sample()
    save_state()


# --------------------------
# CRUD Operations
# --------------------------

def add_document_type(doc_type: DocumentTypeModel | dict[str, Any]) -> DocumentTypeModel:
    """Store a document type in memory and persist it."""
    if isinstance(doc_type, dict):
        doc_type = DocumentTypeModel(**doc_type)
    # Avoid accidental overwrites; callers should use ``update_document_type``
    # when modifying existing entries.  Previously ``add_document_type`` would
    # silently replace an existing document type which caused confusing test
    # failures where a duplicate definition clobbered the original.
    if not doc_type.name.strip():
        raise ValueError("Document type name must not be empty")
    if doc_type.name in document_types:
        raise ValueError(f"Document type '{doc_type.name}' already exists")
    document_types[doc_type.name] = doc_type
    save_state()
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

    save_state()
    return doc_type


def delete_document_type(name: str) -> None:
    """Delete a document type by name and persist changes."""
    try:
        del document_types[name]
        save_state()
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
    try:
        data = json.loads(Path(path).read_text())
    except OSError as exc:
        raise RuntimeError(f"Failed to read document types from {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}") from exc

    if not isinstance(data, list):
        raise ValueError("JSON must contain a list of document types")

    document_types.clear()
    for item in data:
        try:
            doc = DocumentTypeModel(**item)
        except ValidationError as exc:
            raise ValueError(f"Invalid document type entry: {item}") from exc
        document_types[doc.name] = doc
    save_state()


def export_document_types_json() -> str:
    """Return document types as a JSON string."""
    json_data = [doc.model_dump() for doc in document_types.values()]
    return json.dumps(json_data, indent=2)


def import_document_types_json(data: str) -> None:
    """Load document types from a JSON string and persist."""
    try:
        payload = json.loads(data)
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid JSON payload") from exc

    if not isinstance(payload, list):
        raise ValueError("JSON must contain a list of document types")

    document_types.clear()
    for item in payload:
        try:
            doc = DocumentTypeModel(**item)
        except ValidationError as exc:
            raise ValueError(f"Invalid document type entry: {item}") from exc
        document_types[doc.name] = doc
    save_state()


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

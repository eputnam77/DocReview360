"""In-memory document type management."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from pydantic import BaseModel, ValidationError


class DocumentTypeModel(BaseModel):
    """Schema for document types with optional default template linkage."""

    name: str
    template: str
    workflow: List[str] = []
    default_template_id: str | None = None


document_types: Dict[str, DocumentTypeModel] = {}


def _bootstrap_sample() -> None:
    """Create a default sample document type if none exist."""
    if not document_types:
        document_types["sample"] = DocumentTypeModel(
            name="sample",
            template="<h1>Sample</h1>",
            workflow=["draft", "review", "final"],
        )


_bootstrap_sample()


def add_document_type(doc_type: DocumentTypeModel) -> None:
    """Store a document type in memory."""
    document_types[doc_type.name] = doc_type


def get_document_type(name: str) -> DocumentTypeModel | None:
    """Retrieve a document type by name."""
    return document_types.get(name)


def list_document_types() -> list[DocumentTypeModel]:
    """Return all known document types."""
    return list(document_types.values())


def update_document_type(name: str, doc_type: DocumentTypeModel) -> DocumentTypeModel:
    """Update an existing document type."""
    if name not in document_types:
        raise KeyError(f"Document type '{name}' not found")
    document_types[name] = doc_type
    return doc_type


def delete_document_type(name: str) -> None:
    """Delete a document type by name."""
    try:
        del document_types[name]
    except KeyError as exc:
        raise KeyError(f"Document type '{name}' not found") from exc


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
    """Load document types from a JSON file."""
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


def export_document_types_json() -> str:
    """Return document types as a JSON string."""
    json_data = [doc.model_dump() for doc in document_types.values()]
    return json.dumps(json_data, indent=2)


def import_document_types_json(data: str) -> None:
    """Load document types from a JSON string."""
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

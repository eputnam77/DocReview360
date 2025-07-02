"""In-memory document type management."""

from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel


class DocumentTypeModel(BaseModel):
    """Schema for document types."""

    name: str
    template: str
    workflow: List[str] = []


document_types: Dict[str, DocumentTypeModel] = {}


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

"""In-memory document storage and import helpers."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Dict, List, Optional
from uuid import uuid4
from xml.etree.ElementTree import XML
from zipfile import ZipFile

from pydantic import BaseModel


class DocumentModel(BaseModel):
    """Simple representation of a document with revision history."""

    id: str
    content: str
    history: List[str] = []
    number: int | None = None
    project: Optional[str] = None
    user: Optional[str] = None
    date: Optional[datetime] = None
    priority: Optional[int] = None


documents: Dict[str, DocumentModel] = {}
# Track document numbers globally and per project
_next_document_number = 1
_project_document_numbers: Dict[str, int] = {}


def next_document_number(project: Optional[str] = None) -> int:
    """Return the next sequential document number for the project."""
    if project:
        current = _project_document_numbers.get(project, 0) + 1
        _project_document_numbers[project] = current
        return current
    global _next_document_number
    num = _next_document_number
    _next_document_number += 1
    return num


def _extract_docx_text(data: bytes) -> str:
    """Extract text from a DOCX file using minimal parsing.

    This helper only looks for ``word/document.xml`` and ignores styles or
    complex formatting. It is sufficient for tests and small example files but
    should be replaced with a full parser for production use.
    """
    with ZipFile(BytesIO(data)) as zf:
        xml_data = zf.read("word/document.xml")
    root = XML(xml_data)
    texts = [
        node.text or ""
        for node in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")
    ]
    return "".join(texts)


def import_document(
    filename: str,
    data: bytes,
    *,
    project: Optional[str] = None,
    user: Optional[str] = None,
    priority: Optional[int] = None,
) -> DocumentModel:
    """Create a document from uploaded bytes."""
    if filename.lower().endswith(".docx"):
        content = _extract_docx_text(data)
    else:
        content = data.decode()
    doc_id = uuid4().hex
    document = DocumentModel(
        id=doc_id,
        content=content,
        history=[],
        number=next_document_number(project),
        project=project,
        user=user,
        date=datetime.utcnow(),
        priority=priority,
    )
    documents[doc_id] = document
    # Index the document for search without creating an import cycle
    from . import search as search_module

    search_module.add_document(document)
    return document


def get_document(doc_id: str) -> DocumentModel | None:
    """Return a document by id."""
    return documents.get(doc_id)


def list_documents() -> list[DocumentModel]:
    """Return all documents."""
    return list(documents.values())


def update_document(
    doc_id: str,
    content: str,
    *,
    priority: Optional[int] = None,
) -> DocumentModel:
    """Replace document content and store previous version as history."""
    document = documents.get(doc_id)
    if document is None:
        raise KeyError(f"Document '{doc_id}' not found")
    # Remove the old version from the search index before updating
    from . import search as search_module

    search_module.search_index.remove_document(doc_id)

    document.history.append(document.content)
    document.content = content
    if priority is not None:
        document.priority = priority

    # Re-index the updated document
    search_module.add_document(document)

    return document


def autosave_document(doc_id: str, content: str) -> DocumentModel:
    """Save content if it changed, preserving history."""
    document = documents.get(doc_id)
    if document is None:
        raise KeyError(f"Document '{doc_id}' not found")
    if document.content == content:
        return document
    return update_document(doc_id, content)

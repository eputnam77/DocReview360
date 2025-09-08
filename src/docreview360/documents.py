"""In-memory document storage and import helpers."""

from __future__ import annotations

import hashlib
import threading
from base64 import b64encode
from datetime import datetime, timezone
from difflib import SequenceMatcher
from io import BytesIO
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_serializer

from . import fts
from .audit import log_audit_event
from .logs import log_event


class DocumentRevision(BaseModel):
    """Single revision of a document."""

    id: str
    timestamp: datetime
    content: str
    steps: list[Any] | None = None
    author: str = ""
    yjs_updates: list[bytes] | None = None

    @field_serializer("yjs_updates", when_used="json")
    def _ser_updates(self, updates: list[bytes] | None) -> list[str] | None:
        """Return base64 strings for binary Yjs updates.

        ``pydantic`` attempts to decode ``bytes`` as UTF-8 when serialising to
        JSON which fails for arbitrary binary data.  The dashboard API
        serialises full document models including revision history; any binary
        ``yjs_updates`` therefore triggered ``UnicodeDecodeError`` during
        ``model_dump``.  Encoding the updates as base64 preserves the data while
        keeping the output JSON serialisable.
        """

        if updates is None:
            return None
        return [b64encode(u).decode("ascii") for u in updates]


class DocumentModel(BaseModel):
    """Simple representation of a document with revision history."""

    id: str
    content: str
    history: List[DocumentRevision] = Field(default_factory=list)
    editor: str = "tiptap"
    number: int | None = None
    project: Optional[str] = None
    user: Optional[str] = None
    date: Optional[datetime] = None
    priority: Optional[int] = None
    ingestion_hash: str | None = None  # SHA-256 of original upload
    # Flag to mark public copies and track originating document
    public_copy: bool = False
    source_document_id: str | None = None
    # ``approval_ids`` previously used a mutable list as the default value.
    # In ``pydantic`` models this list is shared between instances which meant
    # adding an approval to one document unexpectedly appeared on others.
    # Using ``default_factory`` gives each model its own list.
    approval_ids: List[str] = Field(default_factory=list)


# Stored documents keyed by id
documents: Dict[str, DocumentModel] = {}
# Document ids that require a new review cycle
_re_review: set[str] = set()
# Track document numbers globally and per project
_next_document_number = 1
_project_document_numbers: Dict[str, int] = {}

# Guard shared document state in multithreaded scenarios
document_lock = threading.Lock()


def next_document_number(project: Optional[str] = None) -> int:
    """Return the next sequential document number for the project."""
    with document_lock:
        if project:
            current = _project_document_numbers.get(project, 0) + 1
            _project_document_numbers[project] = current
            return current
        global _next_document_number
        num = _next_document_number
        _next_document_number += 1
        return num




def _extract_docx_text(data: bytes) -> str:
    """Extract text from a DOCX file using ``python-docx``.

    Headings become Markdown ``#`` prefixes and tracked changes are represented
    with ``[INS:...]`` and ``[DEL:...]`` markers.
    """
    from docx import Document

    doc = Document(BytesIO(data))
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    parts: list[str] = []

    for para in doc.paragraphs:
        style = para.style.name if para.style is not None else ""
        prefix = ""
        if style.startswith("Heading"):
            try:
                level = int(style.split()[1])
            except (IndexError, ValueError):
                level = 1
            prefix = "#" * level + " "

        text_piece = ""
        for child in para._element.iterchildren():
            if child.tag == f"{ns}r":
                text_piece += "".join(t.text or "" for t in child.iter(f"{ns}t"))
            elif child.tag == f"{ns}ins":
                ins_text = "".join(t.text or "" for t in child.iter(f"{ns}t"))
                text_piece += f"[INS:{ins_text}]"
            elif child.tag == f"{ns}del":
                del_text = "".join(t.text or "" for t in child.iter(f"{ns}t"))
                text_piece += f"[DEL:{del_text}]"
        parts.append(prefix + text_piece)

    return "\\n".join(parts)


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
    ingestion_hash = hashlib.sha256(data).hexdigest()
    revision = DocumentRevision(
        id=uuid4().hex,
        timestamp=datetime.now(timezone.utc),
        content=content,
        steps=None,
        author=user or "",
    )
    document = DocumentModel(
        id=doc_id,
        content=content,
        history=[revision],
        number=next_document_number(project),
        project=project,
        user=user,
        date=datetime.now(timezone.utc),
        priority=priority,
        ingestion_hash=ingestion_hash,
    )
    with document_lock:
        documents[doc_id] = document
    # Index the document for search without creating an import cycle
    from . import search as search_module

    search_module.add_document(document)
    fts.index_document(doc_id, content)
    log_audit_event(
        doc_id,
        "created",
        actor=user,
        project=project,
        filename=filename,
    )
    return document


def get_document(doc_id: str) -> DocumentModel | None:
    """Return a document by id."""
    return documents.get(doc_id)


def list_documents() -> list[DocumentModel]:
    """Return all documents."""
    return list(documents.values())


def list_public_documents() -> list[DocumentModel]:
    """Return documents marked as public copies."""
    return [d for d in documents.values() if d.public_copy]


def public_documents_report() -> list[dict[str, str | None]]:
    """Return minimal metadata for public documents.

    Each entry contains the public document id and the originating
    ``source_document_id`` so external systems can trace back to the
    internal record.
    """
    return [
        {"id": d.id, "source_document_id": d.source_document_id}
        for d in documents.values()
        if d.public_copy
    ]


def link_approval(doc_id: str, approval_id: str) -> None:
    """Associate ``approval_id`` with ``doc_id`` and log the action."""
    document = documents.get(doc_id)
    if document is None:
        raise KeyError("document not found")
    if approval_id not in document.approval_ids:
        document.approval_ids.append(approval_id)
        log_event(
            "approval_linked",
            doc_id=doc_id,
            approval_id=approval_id,
        )
        log_audit_event(doc_id, "approval_linked", approval_id=approval_id)


def unlink_approval(doc_id: str, approval_id: str) -> None:
    """Remove ``approval_id`` from ``doc_id`` and log the action."""
    document = documents.get(doc_id)
    if document is None:
        return
    if approval_id in document.approval_ids:
        document.approval_ids.remove(approval_id)
        log_event(
            "approval_unlinked",
            doc_id=doc_id,
            approval_id=approval_id,
        )
        log_audit_event(doc_id, "approval_unlinked", approval_id=approval_id)


def update_document(
    doc_id: str,
    content: str,
    *,
    priority: Optional[int] = None,
    steps: list[Any] | None = None,
    author: str | None = None,
    yjs_updates: list[bytes] | None = None,
) -> tuple[DocumentModel, str]:
    """Replace document content and record a new revision."""
    document = documents.get(doc_id)
    if document is None:
        raise KeyError(f"Document '{doc_id}' not found")
    # Remove the old version from the search index before updating
    from . import search as search_module

    search_module.search_index.remove_document(doc_id)
    fts.remove_document(doc_id)

    with document_lock:
        old_content = document.content
        revision_id = uuid4().hex
        document.content = content
        document.history.append(
            DocumentRevision(
                id=revision_id,
                timestamp=datetime.now(timezone.utc),
                content=content,
                steps=steps,
                author=author or document.user or "",
                yjs_updates=yjs_updates,
            )
        )
        if priority is not None:
            document.priority = priority
        if author is not None:
            document.user = author

    if SequenceMatcher(None, old_content, content).ratio() < 0.7:
        with document_lock:
            _re_review.add(doc_id)

    # Re-index the updated document
    search_module.add_document(document)
    if document.content:
        fts.index_document(doc_id, document.content)
    log_audit_event(doc_id, "updated", actor=author or document.user, priority=priority)

    return document, revision_id


def autosave_document(doc_id: str, content: str) -> tuple[DocumentModel, str]:
    """Save content if it changed, preserving history."""
    document = documents.get(doc_id)
    if document is None:
        raise KeyError(f"Document '{doc_id}' not found")
    if document.content == content:
        return document, document.history[-1].id
    return update_document(doc_id, content)


def needs_rereview(doc_id: str) -> bool:
    """Return ``True`` if the document was changed substantially."""
    return doc_id in _re_review


def clear_rereview(doc_id: str) -> None:
    """Remove the re-review flag for ``doc_id``."""
    with document_lock:
        _re_review.discard(doc_id)


def get_document_versions(doc_id: str) -> list[str]:
    """Return the list of all versions for ``doc_id``."""
    document = documents.get(doc_id)
    if document is None:
        raise KeyError(f"Document '{doc_id}' not found")
    return [rev.content for rev in document.history]


def get_document_version(doc_id: str, index: int) -> str:
    """Return a specific version for ``doc_id``."""
    versions = get_document_versions(doc_id)
    if index < 0 or index >= len(versions):
        raise IndexError("version index out of range")
    return versions[index]


def set_document_editor(doc_id: str, editor: str) -> DocumentModel:
    """Set the preferred editor for ``doc_id`` and return the document."""
    if not isinstance(editor, str):
        raise TypeError("editor must be a string")
    editor_name = editor.strip()
    if not editor_name:
        raise ValueError("editor required")
    document = documents.get(doc_id)
    if document is None:
        raise KeyError(f"document '{doc_id}' not found")
    document.editor = editor_name
    return document


def get_document_editor(doc_id: str) -> str:
    """Return the preferred editor for ``doc_id``."""
    document = documents.get(doc_id)
    if document is None:
        raise KeyError(f"document '{doc_id}' not found")
    return document.editor

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from .documents import DocumentModel
from .exporter import export_document


class ArchiveRecord(BaseModel):
    """Archived representation of a document in multiple formats."""

    id: str
    document_id: str
    timestamp: datetime
    metadata: Dict[str, Any] = {}
    markdown: bytes
    html: bytes
    docx: bytes
    pdf: bytes

    model_config = ConfigDict(ser_json_bytes="base64")


archives: Dict[str, ArchiveRecord] = {}


def archive_document(
    document: DocumentModel, metadata: Dict[str, Any] | None = None
) -> ArchiveRecord:
    """Store a document snapshot in several formats."""
    md_bytes, _, _ = export_document(document, "markdown")
    html_bytes, _, _ = export_document(document, "html")
    docx_bytes, _, _ = export_document(document, "docx")
    pdf_bytes, _, _ = export_document(document, "pdf")
    record = ArchiveRecord(
        id=uuid4().hex,
        document_id=document.id,
        timestamp=datetime.utcnow(),
        metadata=metadata or {},
        markdown=md_bytes,
        html=html_bytes,
        docx=docx_bytes,
        pdf=pdf_bytes,
    )
    archives[record.id] = record
    return record


def get_archive(archive_id: str) -> ArchiveRecord | None:
    """Return a single archived record by id."""
    return archives.get(archive_id)


def list_archives() -> List[ArchiveRecord]:
    """Return all archived records."""
    return list(archives.values())

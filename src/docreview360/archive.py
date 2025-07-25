"""Simple in-memory archive utilities."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from .documents import DocumentModel
from .exporter import export_document
from .object_storage import upload_file


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
    document: DocumentModel,
    metadata: Dict[str, Any] | None = None,
    *,
    bucket: str | Path = "archive_store",
) -> ArchiveRecord:
    """Store a document snapshot in several formats and persist to disk."""
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

    # Persist each artefact for durability
    base = f"{record.document_id}/{record.id}"
    upload_file(bucket, f"{base}.md", md_bytes)
    upload_file(bucket, f"{base}.html", html_bytes)
    upload_file(bucket, f"{base}.docx", docx_bytes)
    upload_file(bucket, f"{base}.pdf", pdf_bytes)

    return record


def get_archive(archive_id: str) -> ArchiveRecord | None:
    """Return a single archived record by id."""
    return archives.get(archive_id)


def list_archives() -> List[ArchiveRecord]:
    """Return all archived records."""
    return list(archives.values())

"""Simple in-memory archive utilities."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
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

    hashes = {
        "md": sha256(md_bytes).hexdigest(),
        "html": sha256(html_bytes).hexdigest(),
        "docx": sha256(docx_bytes).hexdigest(),
        "pdf": sha256(pdf_bytes).hexdigest(),
    }
    # Build full metadata for the archived record which may include
    # additional fields like ``public_copy`` or ``source_doc_id``.
    meta = metadata.copy() if metadata else {}
    meta.setdefault("version_summary", f"v{len(document.history) + 1}")
    meta.setdefault("retention_policy", "standard")
    if document.public_copy:
        meta.setdefault("public_copy", True)
    if document.source_document_id:
        meta.setdefault("source_doc_id", document.source_document_id)

    record_meta = {"doc_id": document.id, **meta, "hashes": hashes}

    # ``metadata.json`` should only contain the core fields expected by
    # consumers of the archived artefacts.
    metadata_json = {
        "doc_id": document.id,
        "version_summary": meta["version_summary"],
        "retention_policy": meta["retention_policy"],
        "hashes": hashes,
    }

    record = ArchiveRecord(
        id=uuid4().hex,
        document_id=document.id,
        timestamp=datetime.now(timezone.utc),
        metadata=record_meta,
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
    upload_file(bucket, f"{base}.metadata.json", json.dumps(metadata_json).encode())

    return record


def get_archive(archive_id: str) -> ArchiveRecord | None:
    """Return a single archived record by id."""
    return archives.get(archive_id)


def list_archives() -> List[ArchiveRecord]:
    """Return all archived records."""
    return list(archives.values())

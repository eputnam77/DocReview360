"""Simple in-memory archive utilities."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4

from .security_compliance import should_purge
from .settings_manager import load_settings

from pydantic import BaseModel, ConfigDict

from .documents import DocumentModel
from .exporter import export_document
from .object_storage import upload_file
from .reporting import compile_check_report


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
    report_html: bytes | None = None
    report_pdf: bytes | None = None

    model_config = ConfigDict(ser_json_bytes="base64")


archives: Dict[str, ArchiveRecord] = {}


ARCHIVE_RETENTION_DAYS = 365


def archive_document(
    document: DocumentModel,
    metadata: Dict[str, Any] | None = None,
    *,
    bucket: str | Path = "archive_store",
    check_results: Dict[str, Any] | None = None,
) -> ArchiveRecord:
    """Store a document snapshot in several formats and persist to disk."""
    md_bytes, _, _ = export_document(document, "markdown")
    html_bytes, _, _ = export_document(document, "html")
    docx_bytes, _, _ = export_document(document, "docx")
    pdf_bytes, _, _ = export_document(document, "pdf")
    report_html: bytes | None = None
    report_pdf: bytes | None = None
    if check_results:
        report_html, report_pdf = compile_check_report(check_results)

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
        report_html=report_html,
        report_pdf=report_pdf,
    )
    archives[record.id] = record

    # Persist each artefact for durability and track locations for audit
    base = f"{record.document_id}/{record.id}"
    locations: Dict[str, str | None] = {}
    locations["md"] = str(upload_file(bucket, f"{base}.md", md_bytes, append_only=True) or "")
    locations["html"] = str(upload_file(bucket, f"{base}.html", html_bytes, append_only=True) or "")
    locations["docx"] = str(upload_file(bucket, f"{base}.docx", docx_bytes, append_only=True) or "")
    locations["pdf"] = str(upload_file(bucket, f"{base}.pdf", pdf_bytes, append_only=True) or "")
    if report_html:
        locations["report_html"] = str(
            upload_file(bucket, f"{base}.report.html", report_html, append_only=True) or ""
        )
    if report_pdf:
        locations["report_pdf"] = str(
            upload_file(bucket, f"{base}.report.pdf", report_pdf, append_only=True) or ""
        )
    meta["artefact_locations"] = locations
    metadata_json["artefact_locations"] = locations

    # Generate a watermarked public HTML copy when requested
    if document.public_copy:
        ts = datetime.now(timezone.utc).isoformat()
        watermark = html_bytes.decode() + f"\n<!-- verified {ts} -->"
        public_key = f"{base}.public.html"
        public_loc = upload_file(bucket, public_key, watermark.encode(), append_only=True)
        meta["public_copy_url"] = str(public_loc)
        meta["verification_timestamp"] = ts
        metadata_json["public_copy_url"] = str(public_loc)
        metadata_json["verification_timestamp"] = ts

    # Persist metadata after collecting all details
    upload_file(
        bucket,
        f"{base}.metadata.json",
        json.dumps(metadata_json).encode(),
        append_only=True,
    )

    # Update record metadata with final values including locations and
    # optional public copy details
    record.metadata = {"doc_id": document.id, **meta, "hashes": hashes}

    return record


def get_archive(archive_id: str) -> ArchiveRecord | None:
    """Return a single archived record by id."""
    return archives.get(archive_id)


def list_archives() -> List[ArchiveRecord]:
    """Return all archived records."""
    return list(archives.values())


def purge_archives(
    retention_days: int = ARCHIVE_RETENTION_DAYS,
    *,
    bucket: str | Path = "archive_store",
) -> int:
    """Remove archived records older than ``retention_days``.

    Parameters
    ----------
    retention_days:
        Age in days after which archives are removed.
    bucket:
        Root directory where archived artefacts are stored.

    Returns
    -------
    int
        Number of archives removed.
    """

    removed = 0
    for archive_id, record in list(archives.items()):
        if should_purge(record.timestamp, retention_days):
            base_dir = Path(bucket) / record.document_id
            for path in base_dir.glob(f"{archive_id}*"):
                try:
                    path.unlink()
                except Exception:
                    pass
            archives.pop(archive_id, None)
            removed += 1
    return removed


def schedule_archive_purge() -> None:
    """Configure periodic purging of expired archive records."""
    from .celery_app import app

    settings = load_settings()
    cfg = settings.get("archive", {})
    retention = int(cfg.get("retention_days", ARCHIVE_RETENTION_DAYS))
    interval = int(cfg.get("purge_interval_minutes", 60 * 24))
    app.task(name="docreview360.purge_archives")(purge_archives)
    app.conf.beat_schedule = app.conf.get("beat_schedule", {})
    app.conf.beat_schedule["purge_archives"] = {
        "task": "docreview360.purge_archives",
        "schedule": timedelta(minutes=interval),
        "args": (retention,),
    }

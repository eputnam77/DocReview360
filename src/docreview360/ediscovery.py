# SPDX-License-Identifier: MIT
"""eDiscovery export: package documents and audit logs for legal discovery."""

from __future__ import annotations

import csv
import io
import json
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from .models import AuditLog


def export_ediscovery(
    db: Session,
    document_ids: list[str],
    output_path: str,
    include_audit: bool = True,
    exported_by: str = "system",
) -> dict[str, Any]:
    """Package documents and their metadata into a ZIP for legal discovery.

    Args:
        db: SQLAlchemy session used to query audit logs.
        document_ids: List of document IDs to include.
        output_path: Filesystem path for the output ZIP file.
        include_audit: If True, include audit log entries for each document.
        exported_by: Username performing the export (for manifest).

    Returns:
        Summary dict with 'exported', 'file_path', and 'size_bytes'.
    """
    # Lazy import to avoid circular dependencies
    try:
        from .documents import get_document  # type: ignore[import]
    except Exception:
        get_document = None  # type: ignore[assignment]

    exported_count = 0
    manifest: dict[str, Any] = {
        "export_timestamp": datetime.now(timezone.utc).isoformat(),
        "exported_by": exported_by,
        "document_count": len(document_ids),
        "documents": [],
    }

    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for doc_id in document_ids:
            # Attempt to fetch document content
            content: str | None = None
            metadata: dict[str, Any] = {"document_id": doc_id}

            if get_document is not None:
                try:
                    doc = get_document(doc_id)
                    if doc is not None:
                        content = getattr(doc, "content", None) or getattr(doc, "text", "")
                        metadata.update(
                            {
                                "project_id": getattr(doc, "project", None),
                                "document_type": getattr(doc, "type", None),
                                "status": getattr(doc, "status", None),
                                "created": str(getattr(doc, "created", "")),
                                "updated": str(getattr(doc, "updated", "")),
                            }
                        )
                except Exception:
                    pass

            # Write content
            content_text = content or f"[Document {doc_id} — content unavailable]"
            zf.writestr(f"documents/{doc_id}/content.txt", content_text)

            # Write metadata
            zf.writestr(f"documents/{doc_id}/metadata.json", json.dumps(metadata, indent=2))

            # Write audit logs
            if include_audit:
                logs = (
                    db.query(AuditLog)
                    .filter(AuditLog.entity_id == doc_id)
                    .order_by(AuditLog.timestamp)
                    .all()
                )
                buf = io.StringIO()
                writer = csv.writer(buf)
                writer.writerow(
                    ["timestamp", "user_id", "action", "severity", "entity_type", "details"]
                )
                for entry in logs:
                    writer.writerow(
                        [
                            str(entry.timestamp),
                            entry.user_id or "",
                            entry.action,
                            entry.severity,
                            entry.entity_type or "",
                            json.dumps(entry.details or {}),
                        ]
                    )
                zf.writestr(f"documents/{doc_id}/audit_log.csv", buf.getvalue())

            manifest["documents"].append(doc_id)
            exported_count += 1

        # Write manifest
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))

    size_bytes = os.path.getsize(output_path)
    return {
        "exported": exported_count,
        "file_path": output_path,
        "size_bytes": size_bytes,
    }

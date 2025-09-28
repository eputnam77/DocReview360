"""Utilities for TipTap editor conversions."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4

from . import fts
from .documents import DocumentModel, DocumentRevision, documents, next_document_number

"""Utility helpers for TipTap JSON conversions."""


def markdown_to_tiptap(markdown: str) -> Dict[str, Any]:
    """Convert a markdown string to a minimal TipTap JSON structure."""
    paragraphs = []
    for line in markdown.strip().splitlines():
        if line.strip():
            paragraphs.append({"type": "paragraph", "content": [{"type": "text", "text": line}]})
    return {"type": "doc", "content": paragraphs}


def tiptap_to_markdown(data: Dict[str, Any]) -> str:
    """Extract plain text from a simple TipTap JSON document."""
    try:
        paragraphs: List[dict[str, Any]] = data["content"]
    except (KeyError, TypeError) as exc:
        raise ValueError("Invalid TipTap JSON") from exc

    lines = []
    for para in paragraphs:
        if not isinstance(para, dict) or para.get("type") != "paragraph":
            raise ValueError("Invalid TipTap paragraph")
        parts = para.get("content", [])
        if not isinstance(parts, list):
            raise ValueError("Invalid TipTap paragraph")
        text_parts = []
        for part in parts:
            if not isinstance(part, dict):
                raise ValueError("Invalid TipTap paragraph")
            if part.get("type") == "text":
                text_parts.append(part.get("text", ""))
        lines.append("".join(text_parts))
    return "\n".join(lines)


def import_tiptap_document(
    data: Dict[str, Any], *, project: str | None = None, user: str | None = None
) -> DocumentModel:
    """Create a DocumentModel from TipTap JSON."""
    markdown = tiptap_to_markdown(data)
    ingestion_hash = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    doc_id = uuid4().hex
    revision = DocumentRevision(
        id=uuid4().hex,
        timestamp=datetime.now(timezone.utc),
        content=markdown,
        steps=None,
        author=user or "",
    )
    document = DocumentModel(
        id=doc_id,
        content=markdown,
        history=[revision],
        number=next_document_number(project),
        project=project,
        user=user,
        date=datetime.now(timezone.utc),
        ingestion_hash=ingestion_hash,
    )
    documents[doc_id] = document
    from . import search as search_module

    search_module.add_document(document)
    if markdown.strip():
        fts.index_document(doc_id, markdown)
    return document

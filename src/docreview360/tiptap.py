"""Utilities for TipTap editor conversions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4

from .documents import DocumentModel, documents, next_document_number

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
        text = "".join(part.get("text", "") for part in parts if part.get("type") == "text")
        lines.append(text)
    return "\n".join(lines)


def import_tiptap_document(
    data: Dict[str, Any], *, project: str | None = None, user: str | None = None
) -> DocumentModel:
    """Create a DocumentModel from TipTap JSON."""
    markdown = tiptap_to_markdown(data)
    doc_id = uuid4().hex
    document = DocumentModel(
        id=doc_id,
        content=markdown,
        history=[],
        number=next_document_number(project),
        project=project,
        user=user,
        date=datetime.now(timezone.utc),
    )
    documents[doc_id] = document
    from . import search as search_module

    search_module.add_document(document)
    return document

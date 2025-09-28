"""Utilities for TipTap editor conversions."""

from __future__ import annotations

import copy
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Iterable
from uuid import uuid4

from . import fts
from .documents import DocumentModel, DocumentRevision, documents, next_document_number

"""Utility helpers for TipTap JSON conversions."""

_SUPPORTED_MARK_WRAPPERS: dict[str, tuple[str, str]] = {
    "bold": ("**", "**"),
    "italic": ("*", "*"),
}


def markdown_to_tiptap(markdown: str) -> Dict[str, Any]:
    """Convert a markdown string to a minimal TipTap JSON structure."""
    paragraphs = []
    for line in markdown.strip().splitlines():
        if line.strip():
            paragraphs.append({"type": "paragraph", "content": [{"type": "text", "text": line}]})
    return {"type": "doc", "content": paragraphs}


def _require_list(value: Any, message: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(message)
    return value


def _render_marks(text: str, marks: Iterable[dict[str, Any]] | None) -> str:
    if not marks:
        return text

    wrapped = text
    for mark in marks:
        if not isinstance(mark, dict):
            raise ValueError("TipTap mark entries must be objects")
        mark_type = mark.get("type")
        if mark_type not in _SUPPORTED_MARK_WRAPPERS:
            raise ValueError(f"Unsupported TipTap mark type: {mark_type}")
        prefix, suffix = _SUPPORTED_MARK_WRAPPERS[mark_type]
        wrapped = f"{prefix}{wrapped}{suffix}"
    return wrapped


def _render_inline(parts: Iterable[dict[str, Any]] | None) -> str:
    if parts is None:
        return ""

    pieces: list[str] = []
    for part in parts:
        if not isinstance(part, dict):
            raise ValueError("TipTap inline nodes must be objects")
        node_type = part.get("type")
        if node_type == "text":
            text = part.get("text", "")
            marks = part.get("marks")
            if marks is not None and not isinstance(marks, list):
                raise ValueError("TipTap marks must be provided as a list")
            pieces.append(_render_marks(text, marks))
        elif node_type == "hardBreak":
            pieces.append("  \n")
        else:
            raise ValueError(f"Unsupported TipTap node type: {node_type}")
    return "".join(pieces)


def _render_list(
    node: dict[str, Any], *, ordered: bool, indent: str = "", start: int = 1
) -> list[str]:
    items = _require_list(node.get("content"), "TipTap list content must be a list")
    lines: list[str] = []
    for offset, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError("TipTap list items must be objects")
        if item.get("type") != "listItem":
            raise ValueError(f"Unsupported TipTap node type in list: {item.get('type')}")
        lines.extend(
            _render_list_item(
                item,
                indent=indent,
                ordered=ordered,
                index=start + offset if ordered else None,
            )
        )
    return lines


def _render_list_item(
    item: dict[str, Any], *, indent: str, ordered: bool, index: int | None
) -> list[str]:
    children = _require_list(item.get("content"), "TipTap listItem content must be a list")
    marker = f"{index}. " if ordered and index is not None else "- "
    child_indent = indent + ("    " if ordered else "  ")

    lines: list[str] = []
    first_line_emitted = False
    for child in children:
        if not isinstance(child, dict):
            raise ValueError("TipTap listItem children must be objects")
        child_type = child.get("type")
        if child_type == "paragraph":
            paragraph_content = _require_list(
                child.get("content"), "TipTap paragraph content must be a list"
            )
            text = _render_inline(paragraph_content)
            if not first_line_emitted:
                lines.append(f"{indent}{marker}{text}".rstrip())
                first_line_emitted = True
            else:
                lines.append(f"{indent}{' ' * len(marker)}{text}".rstrip())
        elif child_type == "bulletList":
            lines.extend(_render_list(child, ordered=False, indent=child_indent))
        elif child_type == "orderedList":
            start_attr = child.get("attrs", {}).get("start", 1)
            if not isinstance(start_attr, int):
                start_attr = 1
            lines.extend(_render_list(child, ordered=True, indent=child_indent, start=start_attr))
        else:
            raise ValueError(f"Unsupported TipTap node type in listItem: {child_type}")

    if not first_line_emitted:
        lines.append(f"{indent}{marker}".rstrip())

    return lines


def _render_block(node: dict[str, Any]) -> list[str]:
    node_type = node.get("type")
    if node_type == "paragraph":
        content = _require_list(node.get("content"), "TipTap paragraph content must be a list")
        return [_render_inline(content).rstrip()]
    if node_type == "heading":
        attrs = node.get("attrs", {})
        if not isinstance(attrs, dict):
            raise ValueError("TipTap heading attrs must be an object")
        level = attrs.get("level", 1)
        if not isinstance(level, int):
            raise ValueError("TipTap heading level must be an integer")
        level = max(1, min(level, 6))
        content = _require_list(node.get("content"), "TipTap heading content must be a list")
        text = _render_inline(content)
        return [f"{'#' * level} {text}".rstrip()]
    if node_type == "bulletList":
        return _render_list(node, ordered=False)
    if node_type == "orderedList":
        start_attr = node.get("attrs", {}).get("start", 1)
        if not isinstance(start_attr, int):
            start_attr = 1
        return _render_list(node, ordered=True, start=start_attr)
    if node_type == "hardBreak":
        return [""]

    raise ValueError(f"Unsupported TipTap node type: {node_type}")


def tiptap_to_markdown(data: Dict[str, Any]) -> str:
    """Convert a TipTap JSON document to Markdown."""

    if not isinstance(data, dict):
        raise ValueError("TipTap document must be an object")

    doc_type = data.get("type", "doc")
    if doc_type != "doc":
        raise ValueError(f"Unsupported TipTap root type: {doc_type}")

    try:
        content = _require_list(data["content"], "TipTap document content must be a list")
    except KeyError as exc:
        raise ValueError("Invalid TipTap JSON") from exc

    lines: list[str] = []
    for node in content:
        if not isinstance(node, dict):
            raise ValueError("TipTap nodes must be objects")
        lines.extend(_render_block(node))

    return "\n".join(lines).rstrip("\n")


def import_tiptap_document(
    data: Dict[str, Any], *, project: str | None = None, user: str | None = None
) -> DocumentModel:
    """Create a DocumentModel from TipTap JSON."""
    markdown = tiptap_to_markdown(data)
    ingestion_hash = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    doc_id = uuid4().hex
    tiptap_snapshot = copy.deepcopy(data)
    revision = DocumentRevision(
        id=uuid4().hex,
        timestamp=datetime.now(timezone.utc),
        content=markdown,
        steps=[{"type": "tiptap_snapshot", "doc": tiptap_snapshot}],
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

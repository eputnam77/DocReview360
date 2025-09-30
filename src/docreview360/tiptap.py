"""Utilities for TipTap editor conversions."""

from __future__ import annotations

import copy
import hashlib
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, Sequence
from uuid import uuid4

from . import fts
from .documents import DocumentModel, DocumentRevision, documents, next_document_number
from .settings_manager import load_settings

"""Utility helpers for TipTap JSON conversions."""


_DEFAULT_MARK_WRAPPERS: dict[str, tuple[str, str]] = {
    "bold": ("**", "**"),
    "italic": ("*", "*"),
    "strike": ("~~", "~~"),
    "code": ("`", "`"),
    "underline": ("<u>", "</u>"),
}


def _coerce_wrapper(wrapper: Any) -> tuple[str, str] | None:
    """Return ``(prefix, suffix)`` if ``wrapper`` is a 2-tuple like structure."""

    if (
        isinstance(wrapper, Sequence)
        and not isinstance(wrapper, (str, bytes))
        and len(wrapper) == 2
    ):
        prefix, suffix = wrapper  # type: ignore[misc]
    elif isinstance(wrapper, dict):
        prefix = wrapper.get("prefix")
        suffix = wrapper.get("suffix")
    else:
        return None
    if not isinstance(prefix, str) or not isinstance(suffix, str):
        return None
    return prefix, suffix


def _load_mark_wrappers() -> dict[str, tuple[str, str]]:
    """Combine default mark wrappers with user configured extensions."""

    wrappers = dict(_DEFAULT_MARK_WRAPPERS)
    settings = load_settings()
    tiptap_cfg = settings.get("tiptap") if isinstance(settings, dict) else None
    if isinstance(tiptap_cfg, dict):
        extra_wrappers = tiptap_cfg.get("extra_mark_wrappers")
        if isinstance(extra_wrappers, dict):
            for mark_type, wrapper in extra_wrappers.items():
                coerced = _coerce_wrapper(wrapper)
                if coerced:
                    wrappers[str(mark_type)] = coerced
    return wrappers


_SUPPORTED_MARK_WRAPPERS = _load_mark_wrappers()


def _load_block_wrappers() -> dict[str, tuple[str, str]]:
    """Return configured extra block wrappers for custom nodes."""

    settings = load_settings()
    tiptap_cfg = settings.get("tiptap") if isinstance(settings, dict) else None
    wrappers: dict[str, tuple[str, str]] = {}
    if isinstance(tiptap_cfg, dict):
        extra_blocks = tiptap_cfg.get("extra_block_wrappers")
        if isinstance(extra_blocks, dict):
            for node_type, wrapper in extra_blocks.items():
                coerced = _coerce_wrapper(wrapper)
                if coerced:
                    wrappers[str(node_type)] = coerced
    return wrappers


_EXTRA_BLOCK_WRAPPERS = _load_block_wrappers()


def _render_link_mark(text: str, mark: dict[str, Any]) -> str:
    attrs = mark.get("attrs", {})
    if not isinstance(attrs, dict):
        raise ValueError("TipTap link mark attrs must be an object")
    href = attrs.get("href")
    title = attrs.get("title")
    if not isinstance(href, str) or not href:
        return text
    title_part = f' "{title}"' if isinstance(title, str) and title else ""
    return f"[{text}]({href}{title_part})"


_SPECIAL_MARK_RENDERERS: dict[str, Callable[[str, dict[str, Any]], str]] = {
    "link": _render_link_mark,
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
        if not isinstance(mark_type, str):
            raise ValueError("TipTap mark type must be a string")
        if mark_type in _SPECIAL_MARK_RENDERERS:
            wrapped = _SPECIAL_MARK_RENDERERS[mark_type](wrapped, mark)
            continue
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


def _render_paragraph_block(node: dict[str, Any]) -> list[str]:
    content = _require_list(node.get("content"), "TipTap paragraph content must be a list")
    return [_render_inline(content).rstrip()]


def _render_heading_block(node: dict[str, Any]) -> list[str]:
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


def _render_bullet_list_block(node: dict[str, Any]) -> list[str]:
    return _render_list(node, ordered=False)


def _render_ordered_list_block(node: dict[str, Any]) -> list[str]:
    start_attr = node.get("attrs", {}).get("start", 1)
    if not isinstance(start_attr, int):
        start_attr = 1
    return _render_list(node, ordered=True, start=start_attr)


def _render_blockquote_block(node: dict[str, Any]) -> list[str]:
    content = _require_list(node.get("content"), "TipTap blockquote content must be a list")
    lines: list[str] = []
    for child in content:
        if not isinstance(child, dict):
            raise ValueError("TipTap blockquote children must be objects")
        for rendered in _render_block(child):
            prefix = "> " if rendered else ">"
            lines.append(f"{prefix}{rendered}".rstrip())
    return lines or [">"]


def _render_code_block(node: dict[str, Any]) -> list[str]:
    attrs = node.get("attrs", {})
    if not isinstance(attrs, dict):
        raise ValueError("TipTap codeBlock attrs must be an object")
    language = attrs.get("language", "")
    language = language.strip() if isinstance(language, str) else ""
    content = _require_list(node.get("content"), "TipTap codeBlock content must be a list")
    text_parts: list[str] = []
    for part in content:
        if not isinstance(part, dict) or part.get("type") != "text":
            raise ValueError("TipTap codeBlock content must be text nodes")
        text_parts.append(part.get("text", ""))
    code_text = "".join(text_parts)
    # Preserve line endings exactly as in the code block
    code_lines = code_text.splitlines()
    if code_text.endswith("\n"):
        code_lines.append("")
    fence = f"```{language}".rstrip()
    return [fence, *code_lines, "```"]


def _render_horizontal_rule(_: dict[str, Any]) -> list[str]:
    return ["---"]


def _render_hard_break_block(_: dict[str, Any]) -> list[str]:
    return [""]


def _render_table_cell(cell: dict[str, Any]) -> str:
    if cell.get("type") not in {"tableCell", "tableHeader"}:
        raise ValueError(f"Unsupported TipTap table cell type: {cell.get('type')}")
    cell_content = _require_list(cell.get("content"), "TipTap table cell content must be a list")
    lines: list[str] = []
    for item in cell_content:
        if not isinstance(item, dict):
            raise ValueError("TipTap table cell children must be objects")
        if item.get("type") == "paragraph":
            paragraph_content = _require_list(
                item.get("content"), "TipTap paragraph content must be a list"
            )
            text = _render_inline(paragraph_content).strip()
            if text:
                lines.append(text)
        else:
            for rendered in _render_block(item):
                if rendered:
                    lines.append(rendered)
    return "<br>".join(lines)


def _render_table_block(node: dict[str, Any]) -> list[str]:
    rows = _require_list(node.get("content"), "TipTap table content must be a list")
    parsed_rows: list[tuple[list[str], bool]] = []
    for row in rows:
        if not isinstance(row, dict) or row.get("type") != "tableRow":
            raise ValueError("TipTap table rows must be objects of type tableRow")
        cells = _require_list(row.get("content"), "TipTap tableRow content must be a list")
        cell_texts: list[str] = []
        header = True
        for cell in cells:
            cell_texts.append(_render_table_cell(cell))
            header = header and cell.get("type") == "tableHeader"
        parsed_rows.append((cell_texts, header))

    if not parsed_rows:
        return []

    lines: list[str] = []
    header_cells, has_explicit_header = parsed_rows[0]
    lines.append("| " + " | ".join(header_cells) + " |")
    separator = "| " + " | ".join("---" for _ in header_cells) + " |"
    lines.append(separator)
    body_rows = parsed_rows[1:] if has_explicit_header else parsed_rows
    for cells, _ in body_rows:
        lines.append("| " + " | ".join(cells) + " |")

    return lines


_BLOCK_RENDERERS: dict[str, Callable[[dict[str, Any]], list[str]]] = {
    "paragraph": _render_paragraph_block,
    "heading": _render_heading_block,
    "bulletList": _render_bullet_list_block,
    "orderedList": _render_ordered_list_block,
    "blockquote": _render_blockquote_block,
    "codeBlock": _render_code_block,
    "horizontalRule": _render_horizontal_rule,
    "hardBreak": _render_hard_break_block,
    "table": _render_table_block,
}


def _render_block(node: dict[str, Any]) -> list[str]:
    node_type = node.get("type")
    if not isinstance(node_type, str):
        raise ValueError("TipTap node type must be a string")

    renderer = _BLOCK_RENDERERS.get(node_type)
    if renderer is not None:
        return renderer(node)

    if node_type in _EXTRA_BLOCK_WRAPPERS:
        prefix, suffix = _EXTRA_BLOCK_WRAPPERS[node_type]
        content = _require_list(node.get("content"), f"TipTap {node_type} content must be a list")
        wrapped_lines: list[str] = []
        for child in content:
            if not isinstance(child, dict):
                raise ValueError(f"TipTap {node_type} children must be objects")
            for rendered in _render_block(child):
                wrapped_lines.append(f"{prefix}{rendered}{suffix}".rstrip())
        return wrapped_lines

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
    data: Dict[str, Any],
    *,
    project: str | None = None,
    user: str | None = None,
    link_duplicates: bool = False,
) -> DocumentModel:
    """Create a DocumentModel from TipTap JSON."""
    markdown = tiptap_to_markdown(data)
    ingestion_hash = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    for existing in documents.values():
        if existing.ingestion_hash == ingestion_hash:
            if link_duplicates:
                return existing
            raise ValueError("A document with identical content already exists")
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

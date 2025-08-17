"""Export documents to various formats."""

from __future__ import annotations

from html import escape
from io import BytesIO
from typing import Callable, Iterable, Optional
from zipfile import ZipFile

from .documents import DocumentModel

# Customisable guardrails checker; return True if content is invalid
guardrails_checker: Optional[Callable[[str], bool]] = None


def set_guardrails(checker: Callable[[str], bool] | None) -> None:
    """Register a guardrails validation function."""
    global guardrails_checker
    guardrails_checker = checker


def _render_template(template: str, document: DocumentModel) -> str:
    """Return ``template`` formatted with document attributes.

    Supported placeholders are ``id`` and ``number``. Unknown placeholders
    raise :class:`ValueError` to surface configuration issues early.
    """

    try:
        base = template.format(id=document.id, number=document.number or "")
    except KeyError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Unknown placeholder {exc.args[0]!r} in filename template") from exc
    # Avoid path traversal via placeholders
    return base.replace("/", "_").replace("\\", "_")


def export_document(
    document: DocumentModel,
    fmt: str,
    *,
    name_template: str | None = None,
) -> tuple[bytes, str, str]:
    """Convert a document into ``fmt`` and return bytes, media type and filename."""
    fmt = fmt.lower()
    if guardrails_checker is not None and guardrails_checker(document.content):
        raise ValueError("Content failed guardrails validation")
    template = name_template or "{id}"
    base = _render_template(template, document)
    if fmt in ("markdown", "md"):
        data = document.content.encode()
        media = "text/markdown"
        name = f"{base}.md"
    elif fmt in ("html", "htm"):
        body = escape(document.content)
        html_doc = f"<html><body><pre>{body}</pre></body></html>"
        data = html_doc.encode()
        media = "text/html"
        name = f"{base}.html"
    elif fmt == "json":
        data = document.model_dump_json().encode()
        media = "application/json"
        name = f"{base}.json"
    elif fmt == "docx":
        from docx import Document
        from docx.oxml import OxmlElement
        import re

        docx_doc = Document()
        for line in document.content.splitlines():
            m = re.match(r"^(#+)\s+(.*)", line)
            if m:
                level = len(m.group(1))
                text = m.group(2)
                p = docx_doc.add_heading("", level=level)
                line_text = text
            else:
                p = docx_doc.add_paragraph()
                line_text = line

            idx = 0
            for match in re.finditer(r"\[(INS|DEL):(.*?)\]", line_text):
                if match.start() > idx:
                    p.add_run(line_text[idx:match.start()])
                tag, txt = match.group(1).lower(), match.group(2)
                change = OxmlElement(f"w:{tag}")
                r = OxmlElement("w:r")
                t = OxmlElement("w:t")
                t.text = txt
                r.append(t)
                change.append(r)
                p._element.append(change)
                idx = match.end()
            if idx < len(line_text):
                p.add_run(line_text[idx:])

        buffer = BytesIO()
        docx_doc.save(buffer)
        data = buffer.getvalue()
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        name = f"{base}.docx"
    elif fmt == "pdf":
        placeholder = f"PDF-PLACEHOLDER\n{document.content}"
        data = placeholder.encode()
        media = "application/pdf"
        name = f"{base}.pdf"
    else:
        raise ValueError(f"Unsupported format: {fmt}")
    return data, media, name


def preview_document(document: DocumentModel, fmt: str, *, length: int = 30) -> str:
    """Return a human-readable preview of a document export."""
    data, media, _ = export_document(document, fmt)
    text = document.content
    if media.startswith("text/"):
        text = data.decode()
    return text[:length]


def export_batch(
    documents: Iterable[DocumentModel],
    fmt: str,
    *,
    name_template: str | None = None,
) -> bytes:
    """Export multiple documents of the same format as a ZIP archive."""
    buffer = BytesIO()
    with ZipFile(buffer, "w") as zf:
        for doc in documents:
            data, _, name = export_document(doc, fmt, name_template=name_template)
            zf.writestr(name, data)
    return buffer.getvalue()

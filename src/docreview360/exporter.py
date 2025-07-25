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


def export_document(document: DocumentModel, fmt: str) -> tuple[bytes, str, str]:
    """Convert a document into the requested format and return bytes, media type and filename."""
    fmt = fmt.lower()
    if guardrails_checker is not None and guardrails_checker(document.content):
        raise ValueError("Content failed guardrails validation")
    if fmt == "markdown" or fmt == "md":
        data = document.content.encode()
        media = "text/markdown"
        name = f"{document.id}.md"
    elif fmt == "html" or fmt == "htm":
        body = escape(document.content)
        html_doc = f"<html><body><pre>{body}</pre></body></html>"
        data = html_doc.encode()
        media = "text/html"
        name = f"{document.id}.html"
    elif fmt == "docx":
        # Minimal docx with document.xml only
        xml = (
            "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
            "<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'>"
            f"<w:body><w:p><w:r><w:t>{escape(document.content)}</w:t></w:r></w:p></w:body>"
            "</w:document>"
        )
        buffer = BytesIO()
        with ZipFile(buffer, "w") as zf:
            zf.writestr("word/document.xml", xml)
        data = buffer.getvalue()
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        name = f"{document.id}.docx"
    elif fmt == "pdf":
        placeholder = f"PDF-PLACEHOLDER\n{document.content}"
        data = placeholder.encode()
        media = "application/pdf"
        name = f"{document.id}.pdf"
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


def export_batch(documents: Iterable[DocumentModel], fmt: str) -> bytes:
    """Export multiple documents of the same format as a ZIP archive."""
    buffer = BytesIO()
    with ZipFile(buffer, "w") as zf:
        for doc in documents:
            data, _, name = export_document(doc, fmt)
            zf.writestr(name, data)
    return buffer.getvalue()

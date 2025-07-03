from __future__ import annotations

from html import escape
from io import BytesIO
from zipfile import ZipFile

from .documents import DocumentModel


def export_document(document: DocumentModel, fmt: str) -> tuple[bytes, str, str]:
    """Convert a document into the requested format and return bytes, media type and filename."""
    fmt = fmt.lower()
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

# SPDX-License-Identifier: MIT
"""Document conversion utilities.

Supports converting document content between common formats used in the
document review workflow:

- Word (.docx) → Markdown, plain text, HTML
- Markdown → HTML, plain text
- HTML → plain text
- Any text/content → Word (.docx) output
- PDF → plain text (when pypdf is available)

All conversion functions accept and return ``str`` (text) or ``bytes``
(for binary formats like DOCX).  ``convert_document_content`` is the main
entry point for actual conversion; ``convert_document`` is preserved for
backward compatibility with callers that only need the output path.
"""

from __future__ import annotations

import logging
import re
from io import BytesIO
from pathlib import Path

_logger = logging.getLogger(__name__)

# Supported output format identifiers (normalised to lowercase)
SUPPORTED_OUTPUT_FORMATS: frozenset[str] = frozenset(
    {"markdown", "md", "html", "txt", "text", "docx", "word", "pdf"}
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _bytes_to_docx_text(data: bytes) -> str:
    """Extract Markdown-flavoured text from a DOCX binary using python-docx."""
    from docx import Document  # type: ignore[import-untyped]

    doc = Document(BytesIO(data))
    parts: list[str] = []
    for para in doc.paragraphs:
        style_name = para.style.name.lower() if para.style else ""
        if style_name.startswith("heading"):
            try:
                level = int(style_name.split()[-1])
            except (ValueError, IndexError):
                level = 1
            prefix = "#" * min(level, 6)
            parts.append(f"{prefix} {para.text}")
        else:
            parts.append(para.text)
    return "\n\n".join(p for p in parts if p.strip())


def _text_to_html(text: str) -> str:
    """Wrap plain text in a minimal HTML document."""
    escaped = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br>\n")
    )
    return f"<!DOCTYPE html>\n<html><body>\n{escaped}\n</body></html>"


def _markdown_to_html(md_text: str) -> str:
    """Convert Markdown to HTML using markdown-it if available, else basic regex."""
    try:
        from markdown_it import MarkdownIt  # type: ignore[import-untyped]

        return MarkdownIt().render(md_text)
    except ImportError:
        _logger.debug("markdown-it not available; using basic Markdown → HTML conversion")
        html = md_text
        html = re.sub(r"^#{6}\s+(.+)$", r"<h6>\1</h6>", html, flags=re.MULTILINE)
        html = re.sub(r"^#{5}\s+(.+)$", r"<h5>\1</h5>", html, flags=re.MULTILINE)
        html = re.sub(r"^#{4}\s+(.+)$", r"<h4>\1</h4>", html, flags=re.MULTILINE)
        html = re.sub(r"^#{3}\s+(.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
        html = re.sub(r"^#{2}\s+(.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
        html = re.sub(r"^#\s+(.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)
        html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
        html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)
        html = re.sub(r"\n\n+", "</p>\n<p>", html)
        return f"<p>{html}</p>"


def _html_to_text(html: str) -> str:
    """Strip HTML tags to produce plain text."""
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _text_to_docx_bytes(text: str, title: str = "Document") -> bytes:
    """Convert plain text or Markdown-headings text to a DOCX binary."""
    from docx import Document  # type: ignore[import-untyped]

    doc = Document()
    doc.add_heading(title, level=0)
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading_match:
            level = min(len(heading_match.group(1)), 6)
            doc.add_heading(heading_match.group(2), level=level)
        else:
            doc.add_paragraph(stripped)
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _pdf_to_text(data: bytes) -> str:
    """Extract text from a PDF binary using pypdf when available."""
    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]

        reader = PdfReader(BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(p for p in pages if p.strip())
    except ImportError:
        _logger.debug("pypdf not available; returning placeholder PDF text")
        return "[PDF text extraction requires the pypdf package]"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class ConversionResult:
    """Result of a document conversion operation."""

    def __init__(
        self,
        content: str | bytes,
        output_format: str,
        filename: str,
        media_type: str,
    ) -> None:
        self.content = content
        self.output_format = output_format
        self.filename = filename
        self.media_type = media_type

    @property
    def is_binary(self) -> bool:
        """True when ``content`` is bytes (binary format like DOCX)."""
        return isinstance(self.content, bytes)


def convert_document(source: Path, output_format: str) -> Path:
    """Return the expected output path for a conversion.

    This function is preserved for backward compatibility.  For actual content
    conversion, use :func:`convert_document_content` instead.
    """
    fmt = output_format.lower().strip()
    if fmt not in SUPPORTED_OUTPUT_FORMATS:
        raise ValueError(
            f"Unsupported output format {output_format!r}. "
            f"Supported formats: {sorted(SUPPORTED_OUTPUT_FORMATS)}"
        )
    ext_map = {
        "markdown": ".md",
        "md": ".md",
        "txt": ".txt",
        "text": ".txt",
        "html": ".html",
        "docx": ".docx",
        "word": ".docx",
        "pdf": ".pdf",
    }
    return source.with_suffix(ext_map.get(fmt, f".{fmt}"))


def convert_document_content(
    data: bytes,
    source_filename: str,
    output_format: str,
) -> ConversionResult:
    """Convert ``data`` to ``output_format`` and return a :class:`ConversionResult`.

    Supported input formats (detected from ``source_filename`` extension):
    ``.docx``, ``.md``/``.markdown``, ``.html``/``.htm``, ``.txt``, ``.pdf``.

    Supported output formats: ``markdown``/``md``, ``html``, ``txt``/``text``,
    ``docx``/``word``.  PDF output is not yet supported — requests for PDF
    output return plain text with a warning.
    """
    fmt = output_format.lower().strip()
    if fmt not in SUPPORTED_OUTPUT_FORMATS:
        raise ValueError(
            f"Unsupported output format {output_format!r}. "
            f"Supported: {sorted(SUPPORTED_OUTPUT_FORMATS)}"
        )

    stem = Path(source_filename).stem
    src_ext = Path(source_filename).suffix.lower()

    # -- Extract source to intermediate plain text --
    if src_ext == ".docx":
        extracted = _bytes_to_docx_text(data)
    elif src_ext in (".md", ".markdown"):
        extracted = data.decode("utf-8", errors="replace")
    elif src_ext in (".html", ".htm"):
        extracted = _html_to_text(data.decode("utf-8", errors="replace"))
    elif src_ext == ".pdf":
        extracted = _pdf_to_text(data)
    else:
        extracted = data.decode("utf-8", errors="replace")

    # -- Convert to output format --
    if fmt in ("md", "markdown"):
        out_content: str | bytes = extracted
        out_ext, media = ".md", "text/markdown; charset=utf-8"

    elif fmt == "html":
        if src_ext in (".md", ".markdown"):
            out_content = _markdown_to_html(extracted)
        else:
            out_content = _text_to_html(extracted)
        out_ext, media = ".html", "text/html; charset=utf-8"

    elif fmt in ("txt", "text"):
        out_content = extracted
        out_ext, media = ".txt", "text/plain; charset=utf-8"

    elif fmt in ("docx", "word"):
        out_content = _text_to_docx_bytes(extracted, title=stem)
        out_ext = ".docx"
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    else:
        # PDF output not yet implemented
        _logger.warning("PDF output is not yet supported; returning plain text instead")
        out_content = extracted
        out_ext, media = ".txt", "text/plain; charset=utf-8"

    return ConversionResult(
        content=out_content,
        output_format=fmt,
        filename=f"{stem}_converted{out_ext}",
        media_type=media,
    )

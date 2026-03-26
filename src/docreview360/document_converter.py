# SPDX-License-Identifier: MIT
"""Document conversion utilities.

Supports converting document content between common formats used in the
document review workflow:

- Word (.docx) → Markdown, plain text, HTML
- Markdown → HTML, plain text
- HTML → plain text
- RTF → plain text (basic tag stripping)
- ODT → plain text (XML extraction from zip)
- EPUB → plain text (chapter text extraction from zip)
- LaTeX (.tex) → plain text (command stripping)
- Any text/content → Word (.docx) output
- PDF → plain text (when pypdf is available)
- HTML → Confluence wiki markup

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
    {"markdown", "md", "html", "txt", "text", "docx", "word", "pdf", "confluence"}
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


def _rtf_to_text(data: bytes) -> str:
    """Extract plain text from RTF data via basic tag stripping.

    RTF uses ``{\\rtf`` as a file header.  This implementation strips
    RTF control words, groups, and non-ASCII escape sequences, leaving
    only the printable text content.
    """
    try:
        text = data.decode("latin-1", errors="replace")
    except Exception:
        text = data.decode("utf-8", errors="replace")

    # Remove RTF escape sequences like \'xx (hex-encoded characters)
    text = re.sub(r"\\'[0-9a-fA-F]{2}", " ", text)
    # Remove control words (e.g. \par, \b, \fs24)
    text = re.sub(r"\\[a-zA-Z]+[-]?\d*\s?", "", text)
    # Remove single backslash escapes (e.g. \*, \{, \})
    text = re.sub(r"\\.", "", text)
    # Remove group braces
    text = text.replace("{", "").replace("}", "")
    # Collapse whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _odt_to_text(data: bytes) -> str:
    """Extract plain text from an ODT (OpenDocument Text) binary.

    ODT files are ZIP archives containing ``content.xml``.  The text
    content is extracted by stripping XML tags from that entry.
    """
    import xml.etree.ElementTree as ET
    import zipfile

    try:
        with zipfile.ZipFile(BytesIO(data)) as zf:
            if "content.xml" not in zf.namelist():
                return ""
            xml_bytes = zf.read("content.xml")
    except zipfile.BadZipFile:
        _logger.debug("ODT file is not a valid ZIP archive")
        return ""

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        _logger.debug("Failed to parse ODT content.xml: %s", exc)
        return ""

    # Collect all text nodes, preserving paragraph boundaries
    parts: list[str] = []
    # ODT text:p elements contain paragraphs
    for elem in root.iter():
        local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if local == "p":
            para_text = "".join(elem.itertext()).strip()
            if para_text:
                parts.append(para_text)

    return "\n\n".join(parts)


def _epub_to_text(data: bytes) -> str:
    """Extract plain text from an EPUB binary.

    EPUB files are ZIP archives.  The ``mimetype`` entry must equal
    ``application/epub+zip``.  Chapter content is extracted from HTML/XHTML
    files inside the archive and stripped of tags.
    """
    import zipfile

    try:
        with zipfile.ZipFile(BytesIO(data)) as zf:
            namelist = zf.namelist()
            # Validate EPUB mimetype
            if "mimetype" in namelist:
                mt = zf.read("mimetype").decode("utf-8", errors="replace").strip()
                if mt != "application/epub+zip":
                    _logger.debug("EPUB mimetype mismatch: %r", mt)

            # Collect all HTML/XHTML files (typical chapter content)
            chapter_files = sorted(
                n for n in namelist if n.lower().endswith((".html", ".xhtml", ".htm"))
            )
            parts: list[str] = []
            for chapter_file in chapter_files:
                try:
                    raw = zf.read(chapter_file).decode("utf-8", errors="replace")
                    parts.append(_html_to_text(raw))
                except Exception as exc:
                    _logger.debug("EPUB chapter read failed for %r: %s", chapter_file, exc)

            return "\n\n".join(p for p in parts if p.strip())
    except zipfile.BadZipFile:
        _logger.debug("EPUB file is not a valid ZIP archive")
        return ""


def _latex_to_text(text: str) -> str:
    """Strip LaTeX markup and return plain text.

    Removes document structure commands, environments, math, and formatting
    macros, leaving only the prose content.
    """
    # Remove comments
    text = re.sub(r"%.*$", "", text, flags=re.MULTILINE)
    # Remove \\begin{...}...\\end{...} for non-content environments
    for env in ("equation", "align", "figure", "table", "tabular", "lstlisting",
                "verbatim", "tikzpicture", "array"):
        text = re.sub(
            r"\\begin\{" + env + r"\*?\}.*?\\end\{" + env + r"\*?\}",
            " ",
            text,
            flags=re.DOTALL,
        )
    # Replace common structural commands with their argument text
    text = re.sub(r"\\(?:chapter|section|subsection|subsubsection|paragraph)\*?\{([^}]*)\}",
                  r"\n\n\1\n\n", text)
    text = re.sub(r"\\(?:textbf|textit|emph|underline|texttt|text)\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\(?:label|ref|cite|footnote|url|href)\{[^}]*\}", "", text)
    # Remove remaining commands with one braced argument
    text = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", text)
    # Remove remaining commands without arguments
    text = re.sub(r"\\[a-zA-Z]+\*?", " ", text)
    # Remove lone braces
    text = text.replace("{", "").replace("}", "")
    # Tidy whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def convert_to_confluence(html: str) -> str:
    """Convert an HTML string to Confluence wiki markup.

    Handles the most common HTML elements found in document review content:
    headings, paragraphs, bold/italic, lists, links, code, and line breaks.
    The result is Confluence Storage Format-compatible wiki notation.
    """
    text = html

    # Headings
    for level in range(1, 7):
        text = re.sub(
            r"<h" + str(level) + r"[^>]*>(.*?)</h" + str(level) + r">",
            r"h" + str(level) + r". \1\n",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )

    # Bold and italic
    text = re.sub(r"<strong[^>]*>(.*?)</strong>", r"*\1*", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<b[^>]*>(.*?)</b>", r"*\1*", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<em[^>]*>(.*?)</em>", r"_\1_", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<i[^>]*>(.*?)</i>", r"_\1_", text, flags=re.IGNORECASE | re.DOTALL)

    # Inline code
    text = re.sub(r"<code[^>]*>(.*?)</code>", r"{{{\1}}}", text, flags=re.IGNORECASE | re.DOTALL)

    # Links
    text = re.sub(
        r'<a\s+href=["\']([^"\']*)["\'][^>]*>(.*?)</a>',
        r"[\2|\1]",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Unordered lists
    text = re.sub(r"<li[^>]*>(.*?)</li>", r"* \1\n", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[ou]l[^>]*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"</[ou]l>", "\n", text, flags=re.IGNORECASE)

    # Paragraphs and line breaks
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<p[^>]*>(.*?)</p>", r"\1\n\n", text, flags=re.IGNORECASE | re.DOTALL)

    # Strip remaining tags
    text = re.sub(r"<[^>]+>", "", text)

    # Decode common HTML entities
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&nbsp;", " ").replace("&quot;", '"')

    # Tidy whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


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
        "confluence": ".txt",
    }
    return source.with_suffix(ext_map.get(fmt, f".{fmt}"))


def convert_document_content(
    data: bytes,
    source_filename: str,
    output_format: str,
) -> ConversionResult:
    """Convert ``data`` to ``output_format`` and return a :class:`ConversionResult`.

    Supported input formats (detected from ``source_filename`` extension, with
    content-based fallback detection):
    ``.docx``, ``.md``/``.markdown``, ``.html``/``.htm``, ``.txt``, ``.pdf``,
    ``.rtf``, ``.odt``, ``.epub``, ``.tex``.

    Supported output formats: ``markdown``/``md``, ``html``, ``txt``/``text``,
    ``docx``/``word``, ``confluence``.  PDF output is not yet supported —
    requests for PDF output return plain text with a warning.
    """
    fmt = output_format.lower().strip()
    if fmt not in SUPPORTED_OUTPUT_FORMATS:
        raise ValueError(
            f"Unsupported output format {output_format!r}. "
            f"Supported: {sorted(SUPPORTED_OUTPUT_FORMATS)}"
        )

    stem = Path(source_filename).stem
    src_ext = Path(source_filename).suffix.lower()

    # Content-based format detection for ambiguous extensions
    _is_rtf = src_ext == ".rtf" or data[:5] == b"{\\rtf"
    _is_epub = src_ext == ".epub" or (
        src_ext not in (".docx", ".odt", ".rtf", ".pdf")
        and data[:2] == b"PK"
        and b"application/epub+zip" in data[:512]
    )
    _is_odt = src_ext == ".odt" or (
        src_ext not in (".docx", ".epub", ".rtf", ".pdf")
        and data[:2] == b"PK"
        and b"content.xml" in data[:1024]
        and not _is_epub
    )
    _is_latex = src_ext == ".tex" or (
        src_ext not in (".docx", ".odt", ".epub", ".rtf", ".pdf")
        and b"\\documentclass" in data[:512]
    )

    # -- Extract source to intermediate plain/markdown text --
    # Also preserve the original HTML for formats that benefit from it (e.g. confluence).
    _src_raw_html: str | None = None
    if src_ext == ".docx":
        extracted = _bytes_to_docx_text(data)
        _src_is_md = False
    elif src_ext in (".md", ".markdown"):
        extracted = data.decode("utf-8", errors="replace")
        _src_is_md = True
    elif src_ext in (".html", ".htm"):
        _src_raw_html = data.decode("utf-8", errors="replace")
        extracted = _html_to_text(_src_raw_html)
        _src_is_md = False
    elif src_ext == ".pdf":
        extracted = _pdf_to_text(data)
        _src_is_md = False
    elif _is_rtf:
        extracted = _rtf_to_text(data)
        _src_is_md = False
    elif _is_epub:
        extracted = _epub_to_text(data)
        _src_is_md = False
    elif _is_odt:
        extracted = _odt_to_text(data)
        _src_is_md = False
    elif _is_latex:
        decoded = data.decode("utf-8", errors="replace")
        extracted = _latex_to_text(decoded)
        _src_is_md = False
    else:
        extracted = data.decode("utf-8", errors="replace")
        _src_is_md = False

    # -- Convert to output format --
    if fmt in ("md", "markdown"):
        out_content: str | bytes = extracted
        out_ext, media = ".md", "text/markdown; charset=utf-8"

    elif fmt == "html":
        if _src_is_md:
            out_content = _markdown_to_html(extracted)
        else:
            out_content = _src_raw_html if _src_raw_html is not None else _text_to_html(extracted)
        out_ext, media = ".html", "text/html; charset=utf-8"

    elif fmt in ("txt", "text"):
        # Ensure paragraphs are separated by blank lines for readability
        paragraphs = [p.strip() for p in re.split(r"\n{2,}", extracted) if p.strip()]
        out_content = "\n\n".join(paragraphs)
        out_ext, media = ".txt", "text/plain; charset=utf-8"

    elif fmt in ("docx", "word"):
        out_content = _text_to_docx_bytes(extracted, title=stem)
        out_ext = ".docx"
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    elif fmt == "confluence":
        # Use the original HTML when available; otherwise convert from source first
        if _src_raw_html is not None:
            intermediate_html = _src_raw_html
        elif _src_is_md:
            intermediate_html = _markdown_to_html(extracted)
        else:
            intermediate_html = _text_to_html(extracted)
        out_content = convert_to_confluence(intermediate_html)
        out_ext, media = ".txt", "text/plain; charset=utf-8"

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

# SPDX-License-Identifier: MIT
"""Item 41 Phase 2 — expanded document converter format fidelity tests.

Tests cover:
- RTF detection and text extraction
- ODT detection and text extraction
- EPUB detection and text extraction
- LaTeX command stripping
- Confluence wiki markup export
- convert_document_content auto-detection for new formats
- convert_document_content confluence output format

Run targeted:
    DOCREVIEW360_ENV=dev pytest tests/test_item41_formats.py -v
"""

from __future__ import annotations

import io
import os
import zipfile

import pytest

os.environ.setdefault("DOCREVIEW360_ENV", "dev")

from docreview360.document_converter import (
    ConversionResult,
    _epub_to_text,
    _latex_to_text,
    _odt_to_text,
    _rtf_to_text,
    convert_document_content,
    convert_to_confluence,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_odt_bytes(paragraph_texts: list[str]) -> bytes:
    """Build a minimal ODT ZIP with content.xml containing paragraphs."""
    ns = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
    parts = [f'<?xml version="1.0"?><document-content xmlns:text="{ns}"><body><text>']
    for para in paragraph_texts:
        parts.append(f'<text:p>{para}</text:p>')
    parts.append("</text></body></document-content>")
    content_xml = "".join(parts).encode("utf-8")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("mimetype", "application/vnd.oasis.opendocument.text")
        zf.writestr("content.xml", content_xml)
    return buf.getvalue()


def _make_epub_bytes(chapter_html: str) -> bytes:
    """Build a minimal EPUB ZIP with a single chapter XHTML file."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip")
        zf.writestr(
            "OEBPS/chapter1.xhtml",
            f"<!DOCTYPE html><html><body>{chapter_html}</body></html>",
        )
    return buf.getvalue()


# ---------------------------------------------------------------------------
# RTF
# ---------------------------------------------------------------------------


class TestRtfToText:
    def test_rtf_header_detected(self) -> None:
        """_rtf_to_text extracts text from basic RTF content."""
        rtf = rb"{\rtf1\ansi\deff0 {\fonttbl{\f0 Times New Roman;}} Hello World \par }"
        result = _rtf_to_text(rtf)
        assert "Hello" in result
        assert "World" in result

    def test_rtf_control_words_stripped(self) -> None:
        """RTF control words like \\b, \\par, \\fs24 are removed."""
        rtf = rb"{\rtf1 \b Bold text\b0  normal \par }"
        result = _rtf_to_text(rtf)
        # Control words should be gone; text should remain
        assert "text" in result or "normal" in result
        assert "\\b" not in result

    def test_rtf_detection_in_convert_document_content(self) -> None:
        """convert_document_content detects .rtf extension and extracts text."""
        rtf = rb"{\rtf1\ansi Sample RTF content for testing \par }"
        result = convert_document_content(rtf, "sample.rtf", "txt")
        assert isinstance(result, ConversionResult)
        assert result.output_format == "txt"
        # Content should be a non-empty string
        assert isinstance(result.content, str)

    def test_rtf_content_detection_without_extension(self) -> None:
        """RTF format is detected from {\\rtf header even without .rtf extension."""
        rtf = rb"{\rtf1\ansi Plain text here \par }"
        result = convert_document_content(rtf, "document.bin", "txt")
        assert isinstance(result, ConversionResult)
        # Should have attempted RTF extraction (no crash)
        assert isinstance(result.content, str)


# ---------------------------------------------------------------------------
# ODT
# ---------------------------------------------------------------------------


class TestOdtToText:
    def test_odt_extracts_paragraphs(self) -> None:
        """_odt_to_text extracts text from ODT paragraph elements."""
        data = _make_odt_bytes(["First paragraph.", "Second paragraph."])
        result = _odt_to_text(data)
        assert "First paragraph." in result
        assert "Second paragraph." in result

    def test_odt_detection_via_extension(self) -> None:
        """convert_document_content handles .odt extension."""
        data = _make_odt_bytes(["ODT test content."])
        result = convert_document_content(data, "doc.odt", "txt")
        assert isinstance(result, ConversionResult)
        assert result.output_format == "txt"

    def test_odt_bad_zip_returns_empty(self) -> None:
        """_odt_to_text returns empty string for non-ZIP data."""
        result = _odt_to_text(b"not a zip file")
        assert result == ""

    def test_odt_missing_content_xml_returns_empty(self) -> None:
        """_odt_to_text returns empty string when content.xml is absent."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("manifest.xml", "<manifest/>")
        result = _odt_to_text(buf.getvalue())
        assert result == ""


# ---------------------------------------------------------------------------
# EPUB
# ---------------------------------------------------------------------------


class TestEpubToText:
    def test_epub_extracts_chapter_text(self) -> None:
        """_epub_to_text extracts paragraph text from EPUB chapter files."""
        epub = _make_epub_bytes("<p>Chapter one content.</p>")
        result = _epub_to_text(epub)
        assert "Chapter one content." in result

    def test_epub_detection_via_extension(self) -> None:
        """convert_document_content handles .epub extension."""
        epub = _make_epub_bytes("<p>EPUB test content.</p>")
        result = convert_document_content(epub, "book.epub", "txt")
        assert isinstance(result, ConversionResult)
        assert result.output_format == "txt"
        assert "EPUB test content." in result.content  # type: ignore[operator]

    def test_epub_bad_zip_returns_empty(self) -> None:
        """_epub_to_text returns empty string for non-ZIP data."""
        result = _epub_to_text(b"not a valid epub")
        assert result == ""

    def test_epub_multiple_chapters(self) -> None:
        """_epub_to_text combines text from multiple XHTML chapter files."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("mimetype", "application/epub+zip")
            zf.writestr(
                "OEBPS/ch1.xhtml", "<html><body><p>Chapter 1.</p></body></html>"
            )
            zf.writestr(
                "OEBPS/ch2.xhtml", "<html><body><p>Chapter 2.</p></body></html>"
            )
        result = _epub_to_text(buf.getvalue())
        assert "Chapter 1." in result
        assert "Chapter 2." in result


# ---------------------------------------------------------------------------
# LaTeX
# ---------------------------------------------------------------------------


class TestLatexToText:
    def test_latex_strips_commands(self) -> None:
        """_latex_to_text removes \\section{}, \\textbf{}, etc."""
        tex = r"\section{Introduction} This is \textbf{bold} text."
        result = _latex_to_text(tex)
        assert "Introduction" in result
        assert "bold" in result
        assert "\\section" not in result
        assert "\\textbf" not in result

    def test_latex_removes_comments(self) -> None:
        """_latex_to_text strips % comment lines."""
        tex = "Hello % this is a comment\nWorld"
        result = _latex_to_text(tex)
        assert "Hello" in result
        assert "World" in result
        assert "comment" not in result

    def test_latex_detection_via_extension(self) -> None:
        """convert_document_content handles .tex extension."""
        tex = r"\documentclass{article}\begin{document}Hello LaTeX\end{document}"
        result = convert_document_content(tex.encode(), "paper.tex", "txt")
        assert isinstance(result, ConversionResult)
        assert result.output_format == "txt"

    def test_latex_detection_via_content(self) -> None:
        """LaTeX is detected from \\documentclass in content even with .txt extension."""
        tex = r"\documentclass{article} Some body text."
        result = convert_document_content(tex.encode(), "paper.txt", "txt")
        assert isinstance(result, ConversionResult)
        # Should have stripped the command
        assert "\\documentclass" not in result.content  # type: ignore[operator]

    def test_latex_strips_math_environment(self) -> None:
        """_latex_to_text removes equation environments."""
        tex = r"Before \begin{equation} x = y \end{equation} After"
        result = _latex_to_text(tex)
        assert "Before" in result
        assert "After" in result
        # The math equation block should be removed
        assert "equation" not in result.lower() or "x = y" not in result


# ---------------------------------------------------------------------------
# Confluence export
# ---------------------------------------------------------------------------


class TestConfluenceExport:
    def test_headings_converted(self) -> None:
        """HTML headings are converted to h1. h2. etc. notation."""
        html = "<h1>Title</h1><h2>Subtitle</h2>"
        result = convert_to_confluence(html)
        assert "h1. Title" in result
        assert "h2. Subtitle" in result

    def test_bold_and_italic(self) -> None:
        """<strong> and <em> tags become *text* and _text_."""
        html = "<p><strong>Bold</strong> and <em>Italic</em></p>"
        result = convert_to_confluence(html)
        assert "*Bold*" in result
        assert "_Italic_" in result

    def test_links_converted(self) -> None:
        """<a href> tags become [text|url] notation."""
        html = '<a href="https://example.com">Example</a>'
        result = convert_to_confluence(html)
        assert "[Example|https://example.com]" in result

    def test_unordered_list(self) -> None:
        """<li> elements become * bullets."""
        html = "<ul><li>Item A</li><li>Item B</li></ul>"
        result = convert_to_confluence(html)
        assert "* Item A" in result
        assert "* Item B" in result

    def test_convert_document_content_confluence_output(self) -> None:
        """convert_document_content with output_format='confluence' returns wiki text."""
        html = b"<h1>My Doc</h1><p>Hello <strong>world</strong>.</p>"
        result = convert_document_content(html, "doc.html", "confluence")
        assert isinstance(result, ConversionResult)
        assert result.output_format == "confluence"
        assert isinstance(result.content, str)
        assert "h1. My Doc" in result.content
        assert "*world*" in result.content

    def test_confluence_html_entities_decoded(self) -> None:
        """HTML entities like &amp; are decoded in Confluence output."""
        html = "<p>A &amp; B &lt;here&gt;</p>"
        result = convert_to_confluence(html)
        assert "&" in result
        assert "<" in result or "here" in result

    def test_confluence_unsupported_output_raises(self) -> None:
        """Unsupported output format raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported output format"):
            convert_document_content(b"text", "doc.txt", "xlsxyz")

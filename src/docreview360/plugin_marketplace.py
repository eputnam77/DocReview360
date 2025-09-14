"""Simplified plugin installer and marketplace utilities."""

from __future__ import annotations

import copy
import subprocess
import sys
from typing import Any

from .stubs import record_task_completion

# Real PyPI packages relevant to DocReview360's document review functionality
PLUGIN_DATA = {
    "language-tool-python": {
        "name": "Language Tool Python",
        "description": (
            "Advanced grammar and style checking using LanguageTool. "
            "Detects grammar, spelling, and style issues in multiple languages. "
            "Provides detailed suggestions and explanations for corrections."
        ),
        "category": "Document Quality",
        "version": "2.7.1",
        "author": "LanguageTool",
        "tags": ["grammar", "spelling", "style", "multilingual", "corrections"],
        "pypi_name": "language-tool-python"
    },
    "pylanguagetool": {
        "name": "PyLanguageTool",
        "description": (
            "Python wrapper for LanguageTool grammar checker. "
            "Offers comprehensive text analysis with support for 40+ languages "
            "and extensive rule sets for professional writing."
        ),
        "category": "Document Quality",
        "version": "1.0.0",
        "author": "Adrien Vergé",
        "tags": ["grammar", "language", "text-analysis", "writing"],
        "pypi_name": "pylanguagetool"
    },
    "textstat": {
        "name": "TextStat",
        "description": (
            "Text statistics and readability analysis. "
            "Calculates readability scores (Flesch Reading Ease, Gunning Fog Index, etc.) "
            "and provides text complexity metrics for document assessment."
        ),
        "category": "Document Analysis",
        "version": "0.7.3",
        "author": "Shivam Bansal",
        "tags": ["readability", "statistics", "analysis", "metrics"],
        "pypi_name": "textstat"
    },
    "pypdf2": {
        "name": "PyPDF2",
        "description": (
            "Pure Python PDF library for reading, writing, and manipulating PDF files. "
            "Enables PDF text extraction, metadata modification, and document merging "
            "for document processing workflows."
        ),
        "category": "Document Processing",
        "version": "3.0.1",
        "author": "PyPDF2 Contributors",
        "tags": ["pdf", "extraction", "manipulation", "metadata"],
        "pypi_name": "PyPDF2"
    },
    "python-docx": {
        "name": "Python-docx",
        "description": (
            "Create and modify Microsoft Word (.docx) files. "
            "Provides programmatic access to Word documents for content extraction, "
            "modification, and template-based document generation."
        ),
        "category": "Document Processing",
        "version": "1.1.0",
        "author": "Steve Canny",
        "tags": ["word", "docx", "templates", "extraction"],
        "pypi_name": "python-docx"
    },
    "markdown": {
        "name": "Markdown",
        "description": (
            "Python implementation of Markdown. Converts Markdown text to HTML and other formats. "
            "Essential for document format conversion and content processing in review workflows."
        ),
        "category": "Document Processing",
        "version": "3.5.2",
        "author": "Python Markdown",
        "tags": ["markdown", "html", "conversion", "formatting"],
        "pypi_name": "markdown"
    },
    "beautifulsoup4": {
        "name": "Beautiful Soup 4",
        "description": (
            "HTML and XML parser for extracting data from web pages and HTML documents. "
            "Useful for cleaning and processing HTML content in document review workflows."
        ),
        "category": "Document Processing",
        "version": "4.12.2",
        "author": "Leonard Richardson",
        "tags": ["html", "xml", "parsing", "extraction", "cleaning"],
        "pypi_name": "beautifulsoup4"
    },
    "nltk": {
        "name": "Natural Language Toolkit",
        "description": (
            "Comprehensive natural language processing library. "
            "Provides tools for tokenization, part-of-speech tagging, named entity recognition, "
            "and text analysis for document content understanding."
        ),
        "category": "Document Analysis",
        "version": "3.8.1",
        "author": "NLTK Team",
        "tags": ["nlp", "tokenization", "analysis", "language-processing"],
        "pypi_name": "nltk"
    },
    "spacy": {
        "name": "spaCy",
        "description": (
            "Industrial-strength natural language processing library. "
            "Offers fast and accurate text analysis including entity recognition, "
            "dependency parsing, and text classification for document review automation."
        ),
        "category": "Document Analysis",
        "version": "3.7.2",
        "author": "Explosion AI",
        "tags": ["nlp", "entity-recognition", "parsing", "classification"],
        "pypi_name": "spacy"
    },
    "reportlab": {
        "name": "ReportLab",
        "description": (
            "PDF generation library for creating professional reports and documents. "
            "Enables programmatic PDF creation with custom layouts, charts, and formatting "
            "for document export capabilities."
        ),
        "category": "Document Export",
        "version": "4.0.7",
        "author": "ReportLab",
        "tags": ["pdf", "generation", "reports", "charts"],
        "pypi_name": "reportlab"
    },
    "weasyprint": {
        "name": "WeasyPrint",
        "description": (
            "Convert HTML/CSS to PDF with high-quality output. "
            "Renders web pages and HTML documents to PDF format "
            "with support for modern CSS features and responsive layouts."
        ),
        "category": "Document Export",
        "version": "60.2",
        "author": "WeasyPrint",
        "tags": ["pdf", "html", "css", "conversion"],
        "pypi_name": "weasyprint"
    },
    "python-docx-replace": {
        "name": "Python-docx-replace",
        "description": (
            "Template-based document generation for Word documents. "
            "Simplifies creating documents from templates by replacing placeholders "
            "with dynamic content."
        ),
        "category": "Document Processing",
        "version": "1.0.0",
        "author": "Ivan Burlutskiy",
        "tags": ["templates", "word", "generation", "placeholders"],
        "pypi_name": "python-docx-replace"
    }
}


def list_available() -> list[str]:
    """Return the list of installable packages."""
    return sorted(PLUGIN_DATA.keys())


def get_plugin_info(name: str) -> dict[str, Any] | None:
    """Get detailed information about a specific plugin.

    Returning the raw metadata dictionary exposes the internal ``PLUGIN_DATA``
    mapping to accidental mutation by callers.  In tests this manifested when a
    consumer modified the returned structure and permanently altered the
    catalogue.  To keep the registry immutable from the outside we return a deep
    copy so callers can freely manipulate the result without affecting the
    stored definition.
    """

    info = PLUGIN_DATA.get(name)
    if info is None:
        return None
    return copy.deepcopy(info)


def list_plugins_with_info() -> list[dict[str, Any]]:
    """Return detailed information about all available plugins."""
    # ``PLUGIN_DATA`` stores the canonical metadata for each plugin. Returning
    # the raw dictionaries leaks internal state to callers who might
    # accidentally mutate the module level constants.  Tests simulate such
    # modification and previously observed that updating a returned plugin dict
    # changed ``PLUGIN_DATA`` itself.  To avoid these side effects we return
    # deep copies so callers can safely manipulate the result without affecting
    # the catalog.
    return [
        {"id": plugin_id, **copy.deepcopy(plugin_info)}
        for plugin_id, plugin_info in PLUGIN_DATA.items()
    ]


def install_plugin(name: str) -> None:
    """Install a plugin via ``pip``."""
    # Reject names consisting solely of whitespace which previously slipped
    # through the ``not name`` check and produced a confusing "Unknown plugin"
    # error instead of indicating that the caller failed to provide a real
    # identifier.
    if not isinstance(name, str):
        raise TypeError("name must be a string")
    name = name.strip()
    if not name:
        raise ValueError("name is required")

    if name not in PLUGIN_DATA:
        raise ValueError(f"Unknown plugin: {name}")

    # Use the PyPI package name for installation
    pypi_name = PLUGIN_DATA[name].get("pypi_name", name)
    subprocess.check_call([sys.executable, "-m", "pip", "install", str(pypi_name)])
    record_task_completion(145)

# SPDX-License-Identifier: MIT
"""Simplified plugin installer and marketplace utilities."""

from __future__ import annotations

import copy
import subprocess
import sys
import threading
from typing import Any

from .db_store import get_db
from .models import BuiltinPluginStateRecord, OrgToolConfig

# ---------------------------------------------------------------------------
# Core Tool Pack — FSV is the primary integrated tool for DocReview360.
# These entries appear first in the marketplace with a "Core" badge and are
# enabled by default for all organisations.
# ---------------------------------------------------------------------------
CORE_PLUGIN_DATA: dict[str, Any] = {
    "fedstylevalidator": {
        "name": "Federal Style Validator",
        "description": (
            "Core tool for DocReview360. Validates federal-style documents for FAA/DoD "
            "compliance: plain language, acronym definitions, heading structure, "
            "passive voice, regulatory references (21 CFR, ISO, IEC, EU MDR/IVDR), "
            "and Flesch–Kincaid readability. Enabled by default for all organisations."
        ),
        "category": "Core",
        "version": "1.0.0",
        "author": "DocReview360",
        "tags": ["style", "compliance", "readability", "regulatory", "federal"],
        "pypi_name": "govdocverify",
        "is_core": True,
        "is_builtin": True,
    },
    "scdocbuilder": {
        "name": "Special Conditions Doc Builder",
        "description": (
            "Core tool for generating FAA Special Conditions documents. "
            "Automates the structured formatting requirements for SC notices "
            "and provides template-based document assembly. "
            "Enabled by default for all organisations."
        ),
        "category": "Core",
        "version": "1.0.0",
        "author": "DocReview360",
        "tags": ["faa", "special-conditions", "templates", "generation"],
        "pypi_name": None,
        "is_core": True,
        "is_builtin": True,
    },
}

# Real PyPI packages relevant to DocReview360's document review functionality
PLUGIN_DATA = {
    "language-tool-python": {
        "name": "Language Tool Python",
        "description": (
            "Advanced grammar and style checking using LanguageTool. "
            "Detects grammar, spelling, and style issues in multiple languages. "
            "Provides detailed suggestions and explanations for corrections. "
            "Note: most users already have browser-based grammar tools."
        ),
        "category": "Community / Optional",
        "version": "2.7.1",
        "author": "LanguageTool",
        "tags": ["grammar", "spelling", "style", "multilingual", "corrections"],
        "pypi_name": "language-tool-python",
        "is_community": True,
    },
    "pylanguagetool": {
        "name": "PyLanguageTool",
        "description": (
            "Python wrapper for LanguageTool grammar checker. "
            "Offers comprehensive text analysis with support for 40+ languages "
            "and extensive rule sets for professional writing. "
            "Note: most users already have browser-based grammar tools."
        ),
        "category": "Community / Optional",
        "version": "1.0.0",
        "author": "Adrien Vergé",
        "tags": ["grammar", "language", "text-analysis", "writing"],
        "pypi_name": "pylanguagetool",
        "is_community": True,
    },
    "pyspellchecker": {
        "name": "PySpellChecker",
        "description": (
            "Pure Python spell checking library with no external dependencies. "
            "Supports multiple languages and provides word frequency-based correction "
            "suggestions. Note: most users already have browser-based spell checkers."
        ),
        "category": "Community / Optional",
        "version": "0.7.2",
        "author": "Peter Norvig / barrust",
        "tags": ["spelling", "spell-check", "grammar", "corrections"],
        "pypi_name": "pyspellchecker",
        "is_community": True,
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
        "pypi_name": "textstat",
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
        "pypi_name": "PyPDF2",
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
        "pypi_name": "python-docx",
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
        "pypi_name": "markdown",
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
        "pypi_name": "beautifulsoup4",
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
        "pypi_name": "nltk",
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
        "pypi_name": "spacy",
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
        "pypi_name": "reportlab",
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
        "pypi_name": "weasyprint",
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
        "pypi_name": "python-docx-replace",
    },
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
    """Return detailed information about all available plugins.

    Core tools appear first (is_core=True), then non-community plugins, then
    Community / Optional plugins last.  This ensures the most important tools
    are always at the top of the marketplace UI.
    """
    # Core tools come first, always.
    core_entries = [
        {"id": plugin_id, **copy.deepcopy(plugin_info)}
        for plugin_id, plugin_info in CORE_PLUGIN_DATA.items()
    ]
    # Standard + community plugins follow.
    standard_entries = [
        {"id": plugin_id, **copy.deepcopy(plugin_info)}
        for plugin_id, plugin_info in PLUGIN_DATA.items()
    ]
    # Stable sort standard entries: non-community first.
    standard_entries.sort(key=lambda p: (1 if p.get("is_community") else 0))
    return core_entries + standard_entries


# ---------------------------------------------------------------------------
# Built-in plugin enable/disable state
# ---------------------------------------------------------------------------

BUILTIN_PLUGIN_IDS = {"fedstylevalidator", "scdocbuilder"}
_DEFAULT_BUILTIN_STATES: dict[str, bool] = {pid: True for pid in BUILTIN_PLUGIN_IDS}

_builtin_states: dict[str, bool] = dict(_DEFAULT_BUILTIN_STATES)
_builtin_lock = threading.Lock()


def get_builtin_status(org_id: str | None = None) -> dict[str, bool]:
    """Return enabled/disabled state for all built-in plugins.

    Reads persisted state from SQLite, falling back to the in-memory cache
    (which defaults to ``True`` for all plugins) if the DB is unavailable.

    If *org_id* is provided, per-org overrides from ``OrgToolConfig`` are
    applied on top of the global state.
    """
    with _builtin_lock:
        try:
            db = get_db()
            with db.orm_session() as session:
                records = session.query(BuiltinPluginStateRecord).all()
                db_states = {r.plugin_id: r.enabled for r in records}
            # Merge: DB values override the documented defaults; stale in-memory
            # fallback state must not leak into a healthy empty database.
            result: dict[str, bool] = {}
            for pid in BUILTIN_PLUGIN_IDS:
                result[pid] = db_states.get(pid, _DEFAULT_BUILTIN_STATES[pid])
            # Update in-memory cache to stay consistent with DB.
            _builtin_states.update(result)
        except Exception:
            # DB unavailable — fall back to in-memory state.
            result = dict(_builtin_states)

    if org_id:
        try:
            org_cfg = get_org_tool_config(org_id)
            org_overrides: dict[str, bool] = org_cfg.get("enabled_builtins", {})
            for pid, state in org_overrides.items():
                if pid in result:
                    result[pid] = state
        except Exception:
            pass  # Org config unavailable — use global state.

    return result


def set_builtin_plugin_state(plugin_id: str, enabled: bool) -> None:
    """Enable or disable a built-in plugin by ID.

    Persists the new state to SQLite and updates the in-memory cache.
    Falls back to in-memory only if the DB is unavailable.

    Raises ``ValueError`` if ``plugin_id`` is not a known built-in.
    """
    if plugin_id not in BUILTIN_PLUGIN_IDS:
        raise ValueError(f"Unknown built-in plugin: {plugin_id!r}")
    with _builtin_lock:
        try:
            db = get_db()
            with db.orm_session() as session:
                record = session.get(BuiltinPluginStateRecord, plugin_id)
                if record is None:
                    record = BuiltinPluginStateRecord(plugin_id=plugin_id, enabled=enabled)
                    session.add(record)
                else:
                    record.enabled = enabled
        except Exception:
            pass  # DB unavailable — state only updated in memory below.
        _builtin_states[plugin_id] = enabled


# ---------------------------------------------------------------------------
# Per-org tool configuration
# ---------------------------------------------------------------------------


def get_org_tool_config(org_id: str) -> dict[str, Any]:
    """Return the tool configuration for *org_id*.

    Returns a dict with keys:
    - ``org_id``: the org identifier
    - ``disabled_plugins``: list of marketplace plugin IDs disabled for this org
    - ``enabled_builtins``: dict of builtin_id -> bool overrides for this org

    If no config row exists yet the function returns an empty (default) config.
    """
    try:
        db = get_db()
        with db.orm_session() as session:
            record = session.get(OrgToolConfig, org_id)
            if record is None:
                return {
                    "org_id": org_id,
                    "disabled_plugins": [],
                    "enabled_builtins": {},
                }
            return {
                "org_id": org_id,
                "disabled_plugins": record.disabled_plugins or [],
                "enabled_builtins": record.enabled_builtins or {},
            }
    except Exception:
        return {
            "org_id": org_id,
            "disabled_plugins": [],
            "enabled_builtins": {},
        }


def set_org_tool_config(
    org_id: str,
    *,
    disabled_plugins: list[str] | None = None,
    enabled_builtins: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Persist tool configuration overrides for *org_id*.

    Only the keys that are explicitly passed are updated; omitted keys retain
    their current values.  Returns the full config after the update.
    """
    db = get_db()
    with db.orm_session() as session:
        record = session.get(OrgToolConfig, org_id)
        if record is None:
            record = OrgToolConfig(
                org_id=org_id,
                disabled_plugins=[],
                enabled_builtins={},
            )
            session.add(record)
        if disabled_plugins is not None:
            # Validate that supplied plugin IDs are known.
            unknown = [pid for pid in disabled_plugins if pid not in PLUGIN_DATA]
            if unknown:
                raise ValueError(f"Unknown plugin IDs: {unknown}")
            record.disabled_plugins = disabled_plugins
        if enabled_builtins is not None:
            unknown_builtins = [
                bid for bid in enabled_builtins if bid not in BUILTIN_PLUGIN_IDS
            ]
            if unknown_builtins:
                raise ValueError(f"Unknown built-in plugin IDs: {unknown_builtins}")
            record.enabled_builtins = enabled_builtins

    return {
        "org_id": org_id,
        "disabled_plugins": record.disabled_plugins or [],
        "enabled_builtins": record.enabled_builtins or {},
    }


def get_effective_plugins(org_id: str) -> list[dict[str, Any]]:
    """Return the marketplace plugin list for *org_id*, with disabled plugins filtered out."""
    org_cfg = get_org_tool_config(org_id)
    disabled = set(org_cfg.get("disabled_plugins", []))
    all_plugins = list_plugins_with_info()
    for plugin in all_plugins:
        plugin["disabled_for_org"] = plugin["id"] in disabled
    return all_plugins


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

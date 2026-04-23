# SPDX-License-Identifier: MIT
"""Utility for switching between multiple editors."""

from __future__ import annotations

import importlib

from .documents import DocumentModel

EDITOR_PLACEHOLDERS = {
    "tiptap": "tiptap-editor",
    "ckeditor5": "ckeditor5-editor",
}

EDITOR_PLUGINS = {
    "onlyoffice": "docreview360.onlyoffice_editor:OnlyofficeConnector",
}


def render_editor(document: DocumentModel) -> str:
    """Return an HTML snippet for the editor configured on ``document``."""
    # Normalize the editor name so callers can pass values with varying
    # capitalisation or surrounding whitespace.  The previous implementation
    # performed a direct dictionary lookup which meant values like
    # ``" OnlyOffice "`` failed to resolve even though the plugin exists.  By
    # trimming and lower‑casing the name we keep lookups user friendly and avoid
    # surprising ``ValueError`` exceptions.
    name = (document.editor or "tiptap").strip().lower()
    placeholder = EDITOR_PLACEHOLDERS.get(name)
    if placeholder is not None:
        return f"<div id='{placeholder}' data-doc='{document.id}'></div>"
    target = EDITOR_PLUGINS.get(name)
    if target is None:
        raise ValueError(f"unknown editor '{name}'")
    module_name, class_name = target.split(":")
    module = importlib.import_module(module_name)
    cls = getattr(module, class_name)
    return str(cls().open_document(document.id))

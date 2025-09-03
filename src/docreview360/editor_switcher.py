"""Utility for switching between multiple editors."""

from __future__ import annotations

import importlib

from .documents import DocumentModel

# Map editor names to ``module:class`` paths
EDITOR_PLUGINS = {
    "tiptap": None,
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
    target = EDITOR_PLUGINS.get(name)
    if target is None:
        if name != "tiptap":
            raise ValueError(f"unknown editor '{name}'")
        return f"<div id='tiptap-editor' data-doc='{document.id}'></div>"
    module_name, class_name = target.split(":")
    module = importlib.import_module(module_name)
    cls = getattr(module, class_name)
    return str(cls().open_document(document.id))

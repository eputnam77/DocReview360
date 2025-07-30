"""Utility for switching between multiple editors."""

from __future__ import annotations

import importlib

from .documents import DocumentModel

# Map editor names to ``module:class`` paths
EDITOR_PLUGINS = {
    "tiptap": None,
    "onlyoffice": "docreview360.onlyoffice_editor:OnlyofficeConnector",
    "xml": "docreview360.xml_editor:XMLEditor",
}


def render_editor(document: DocumentModel) -> str:
    """Return an HTML snippet for the editor configured on ``document``."""
    name = document.editor
    if not name:
        name = "tiptap"
    target = EDITOR_PLUGINS.get(name)
    if target is None:
        if name != "tiptap":
            raise ValueError(f"unknown editor '{name}'")
        return f"<div id='tiptap-editor' data-doc='{document.id}'></div>"
    module_name, class_name = target.split(":")
    module = importlib.import_module(module_name)
    cls = getattr(module, class_name)
    return str(cls().open_document(document.id))

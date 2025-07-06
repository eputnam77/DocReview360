"""XML editor connector using Monaco."""

from __future__ import annotations

from .stubs import record_task_completion


class XMLEditor:
    """Return HTML snippet embedding a Monaco XML editor."""

    def open_document(self, doc_id: str) -> str:
        """Return an HTML div placeholder for the editor."""
        if not doc_id:
            raise ValueError("doc_id required")
        record_task_completion(161)
        return f"<div id='xml-editor' data-doc='{doc_id}'></div>"

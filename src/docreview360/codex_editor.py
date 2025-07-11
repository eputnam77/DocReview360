"""CodeX editor connector stub."""

from __future__ import annotations

from .stubs import record_task_completion


class CodeXEditor:
    """Return HTML snippet embedding the CodeX block editor."""

    def open_document(self, doc_id: str) -> str:
        """Return an HTML div placeholder for the CodeX editor."""
        if not doc_id:
            raise ValueError("doc_id required")
        record_task_completion(162)
        return f"<div id='codex-editor' data-doc='{doc_id}'></div>"

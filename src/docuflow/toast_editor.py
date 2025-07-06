"""Toast UI editor connector."""

from __future__ import annotations

from .stubs import record_task_completion


class ToastEditor:
    """Return HTML snippet embedding the Toast UI editor."""

    def open_document(self, doc_id: str) -> str:
        """Return an HTML div placeholder for the editor."""
        if not doc_id:
            raise ValueError("doc_id required")
        record_task_completion(160)
        return f"<div id='toast-editor' data-doc='{doc_id}'></div>"

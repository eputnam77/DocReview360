"""ONLYOFFICE Docs connector stub."""

from __future__ import annotations

from . import record_task_completion


class OnlyofficeConnector:
    """Provide an HTML iframe snippet for a document."""

    def open_document(self, doc_id: str) -> str:
        """Return an iframe snippet pointing to the editor."""
        record_task_completion(79)
        return f"<iframe src='/onlyoffice/{doc_id}'></iframe>"

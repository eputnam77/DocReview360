"""Alfresco ECM connector stub."""

from __future__ import annotations

from . import record_task_completion

STORAGE: dict[str, str] = {}


class AlfrescoClient:
    """Very small client storing docs in memory."""

    def upload_document(self, doc_id: str, content: str) -> None:
        """Save ``content`` identified by ``doc_id``."""
        if not doc_id:
            raise ValueError("doc_id required")
        STORAGE[doc_id] = content
        record_task_completion(81)

    def download_document(self, doc_id: str) -> str:
        """Return the stored document for ``doc_id``."""
        if doc_id not in STORAGE:
            raise KeyError(doc_id)
        return STORAGE[doc_id]

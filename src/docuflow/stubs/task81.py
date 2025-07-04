"""Alfresco ECM connector stub."""

from __future__ import annotations

from . import record_task_completion

STORAGE: dict[str, str] = {}


class AlfrescoClient:
    """Very small client storing docs in memory."""

    def upload_document(self, doc_id: str, content: str) -> None:
        STORAGE[doc_id] = content
        record_task_completion(81)

    def download_document(self, doc_id: str) -> str:
        return STORAGE[doc_id]

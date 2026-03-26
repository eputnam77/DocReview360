# SPDX-License-Identifier: MIT
"""Document service — business logic wrapper around document CRUD operations."""

from __future__ import annotations

import logging
from typing import Optional

from ..documents._models import DocumentModel

_logger = logging.getLogger(__name__)


class DocumentService:
    """Thin service layer for document lifecycle operations.

    Wraps the lower-level ``documents`` module so that routers stay thin and
    business rules are testable without an HTTP layer.
    """

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get(self, doc_id: str) -> Optional[DocumentModel]:
        """Return a document by ID or ``None`` if it does not exist."""
        from ..documents import get_document

        return get_document(doc_id)

    def list(self) -> list[DocumentModel]:
        """Return all documents."""
        from ..documents import list_documents

        return list_documents()

    def list_public(self) -> list[DocumentModel]:
        """Return documents marked as publicly visible."""
        from ..documents import list_public_documents

        return list_public_documents()

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def update_editor(self, doc_id: str, editor: str) -> DocumentModel:
        """Switch the active editor for a document."""
        from ..documents import set_document_editor

        _logger.info("Setting editor for document %s to %r", doc_id, editor)
        return set_document_editor(doc_id, editor)

    def autosave(self, doc_id: str, content: str) -> tuple[DocumentModel, str]:
        """Persist an autosave snapshot and return (document, diff_summary)."""
        from ..documents import autosave_document

        return autosave_document(doc_id, content)

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def assert_exists(self, doc_id: str) -> DocumentModel:
        """Return the document or raise ``KeyError`` if it does not exist."""
        doc = self.get(doc_id)
        if doc is None:
            raise KeyError(f"Document not found: {doc_id}")
        return doc

    def is_frozen(self, doc_id: str) -> bool:
        """Return ``True`` when the document is frozen (read-only)."""
        doc = self.get(doc_id)
        return bool(doc and doc.frozen)

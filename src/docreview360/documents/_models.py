# SPDX-License-Identifier: MIT
"""Document data models — DocumentModel, DocumentRevision, FrozenDocumentError."""

from __future__ import annotations

import threading
from base64 import b64encode
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_serializer


class DocumentRevision(BaseModel):
    """Single revision of a document."""

    id: str
    timestamp: datetime
    content: str
    steps: list[Any] | None = None
    author: str = ""
    yjs_updates: list[bytes] | None = None

    @field_serializer("yjs_updates", when_used="json")
    def _ser_updates(self, updates: list[bytes] | None) -> list[str] | None:
        """Return base64 strings for binary Yjs updates."""
        if updates is None:
            return None
        return [b64encode(u).decode("ascii") for u in updates]


class DocumentModel(BaseModel):
    """Simple representation of a document with revision history."""

    id: str
    content: str
    history: List[DocumentRevision] = Field(default_factory=list)
    editor: str = "tiptap"
    number: int | None = None
    project: Optional[str] = None
    user: Optional[str] = None
    date: Optional[datetime] = None
    priority: Optional[int] = None
    ingestion_hash: str | None = None  # SHA-256 of original upload
    public_copy: bool = False
    source_document_id: str | None = None
    approval_ids: List[str] = Field(default_factory=list)
    # Version lineage fields
    version_number: int = 1
    """Monotonically increasing integer incremented on every successful update."""
    frozen: bool = False
    """When True, update_document() raises FrozenDocumentError instead of modifying content."""


class FrozenDocumentError(RuntimeError):
    """Raised when attempting to modify a document that has been frozen."""


# Stored documents keyed by id
documents: Dict[str, DocumentModel] = {}
# Document ids that require a new review cycle
_re_review: set[str] = set()
# Track document numbers globally and per project
_next_document_number = 1
_project_document_numbers: Dict[str, int] = {}

# Guard shared document state in multithreaded scenarios
document_lock = threading.Lock()

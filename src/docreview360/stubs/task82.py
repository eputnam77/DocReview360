"""OpenSearch backend stub."""

from __future__ import annotations

from . import record_task_completion


class OpenSearchClient:
    """In-memory search index."""

    def __init__(self) -> None:
        self.index: list[str] = []

    def index_document(self, doc: str) -> None:
        """Add ``doc`` to the index."""
        if not doc:
            raise ValueError("doc must be non-empty")
        self.index.append(doc)
        record_task_completion(82)

    def search(self, query: str) -> list[str]:
        """Return indexed documents matching ``query``."""
        if not query:
            return []
        return [d for d in self.index if query.lower() in d.lower()]

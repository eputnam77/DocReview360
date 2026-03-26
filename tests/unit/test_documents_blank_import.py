from __future__ import annotations

import pytest
from docreview360 import documents


def test_import_document_allows_blank_content(monkeypatch: pytest.MonkeyPatch) -> None:
    """Blank uploads should produce a document without search indexing errors."""

    calls: list[tuple[str, str]] = []

    def _index(doc_id: str, content: str) -> None:
        calls.append((doc_id, content))

    import sys
    monkeypatch.setattr(sys.modules["docreview360.documents._store"].fts, "index_document", _index)
    monkeypatch.setattr("docreview360.documents._store.log_audit_event", lambda *args, **kwargs: None)

    doc = documents.import_document("empty.txt", b"   ")
    try:
        assert doc.content == "   "
        assert calls == []
    finally:
        documents.documents.pop(doc.id, None)

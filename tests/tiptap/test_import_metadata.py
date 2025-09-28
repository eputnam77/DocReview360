"""Regression tests for TipTap document ingestion metadata."""

from __future__ import annotations

import hashlib

from docreview360 import documents as documents_module
from docreview360 import search as search_module
from docreview360.tiptap import import_tiptap_document, markdown_to_tiptap


def test_import_sets_ingestion_hash_and_indexes(monkeypatch) -> None:
    """TipTap imports should compute hashes and update the FTS index."""

    calls: list[tuple[str, str]] = []

    def fake_index(doc_id: str, content: str) -> None:
        calls.append((doc_id, content))

    monkeypatch.setattr("docreview360.tiptap.fts.index_document", fake_index)

    markdown = "TipTap metadata regression"
    document = import_tiptap_document(markdown_to_tiptap(markdown))

    expected_hash = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    assert document.ingestion_hash == expected_hash
    assert calls == [(document.id, markdown)]

    # Cleanup shared state mutated during import to avoid bleeding between tests.
    search_module.search_index.remove_document(document.id)
    documents_module.documents.pop(document.id, None)

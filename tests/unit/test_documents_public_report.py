"""Regression tests for public document reporting helpers."""

from __future__ import annotations

from copy import deepcopy

from docreview360.documents import DocumentModel, documents, public_documents_report


def test_public_documents_report_filters_non_public_documents() -> None:
    """Only documents marked as public copies should appear in the report."""

    original_docs = deepcopy(documents)
    try:
        documents.clear()
        private = DocumentModel(
            id="doc-private",
            content="internal",
            history=[],
        )
        public = DocumentModel(
            id="doc-public",
            content="public",
            history=[],
            public_copy=True,
            source_document_id="original-id",
        )
        documents[private.id] = private
        documents[public.id] = public

        report = public_documents_report()

        assert report == [{"id": "doc-public", "source_document_id": "original-id"}]
    finally:
        documents.clear()
        documents.update(original_docs)

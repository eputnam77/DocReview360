from unittest.mock import patch

import pytest
from docreview360.cache import cache_get, cache_set, clear_cache
from docreview360.documents import DocumentModel, document_lock, documents
from docreview360.search import add_document, search


def test_search_drops_corrupted_cache_on_error(monkeypatch: pytest.MonkeyPatch):
    # Ensure no leftover Redis stub from other tests so cache ops use _cache dict.
    # Use string-form setattr so monkeypatch always patches the module currently
    # registered in sys.modules (not a potentially stale local reference).
    monkeypatch.setattr("docreview360.cache._client", None)
    monkeypatch.setattr("docreview360.cache._redis", None)

    with document_lock:
        documents.clear()
        doc = DocumentModel(id="1", content="hello world")
        documents[doc.id] = doc
    add_document(doc)

    clear_cache()
    cache_key = "search-core-hello-----"
    cache_set(cache_key, "not-json")

    # Force cache_set in search() to fail so corrupted entry would persist
    with patch("docreview360.cache.cache_set", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            search("hello")

    # Corrupted cache entry should have been removed despite error
    assert cache_get(cache_key) is None

from docreview360.cache import clear_cache
from docreview360.documents import documents, import_document
from docreview360.search import search, search_index


def test_search_caches_results() -> None:
    clear_cache()
    search_index.index.clear()
    documents.clear()

    doc = import_document("a.md", b"foo bar")

    first = search("foo")
    assert first and first[0].id == doc.id

    search_index.remove_document(doc.id)
    documents.pop(doc.id)

    second = search("foo")
    assert second and second[0].id == doc.id


def test_search_cache_handles_bytes() -> None:
    clear_cache()
    search_index.index.clear()
    documents.clear()

    doc = import_document("b.md", b"hello world")
    # prime cache
    search("hello")
    key = "search-core-hello---"
    from json import dumps

    from docreview360.cache import cache_set

    cache_set(key, dumps([{"id": doc.id, "content": "cached"}]).encode(), ttl=30)
    result = search("hello")
    assert result and result[0].id == doc.id

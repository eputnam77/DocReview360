import pytest
from docreview360 import search


def test_saved_search_and_stats() -> None:
    search.saved_searches.clear()
    search.search_counter.clear()
    search.save_search("alpha", user="bob")
    search.search("alpha")
    search.search("alpha")
    stats = search.search_stats()
    assert stats["alpha"] == 2
    saved = search.list_saved_searches("bob")
    assert any(s.query == "alpha" for s in saved)


def test_save_search_rejects_empty_query() -> None:
    search.saved_searches.clear()
    with pytest.raises(ValueError):
        search.save_search("  ", user="bob")

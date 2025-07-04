import pytest

from docuflow import vector_search


def test_vector_search_ranking() -> None:
    vector_search.clear()
    vector_search.index_document("a", "alpha beta")
    vector_search.index_document("b", "beta gamma")
    results = vector_search.search("alpha")
    assert results[0][0] == "a"


def test_vector_search_invalid() -> None:
    vector_search.clear()
    with pytest.raises(ValueError):
        vector_search.index_document("", "x")
    with pytest.raises(ValueError):
        vector_search.search(" ")

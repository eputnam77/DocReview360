from docreview360 import vector_search


def test_embedding_ignores_punctuation() -> None:
    vector_search.clear()
    vector_search.index_document("1", "Hello, world!")
    results = vector_search.search("world")
    assert results[0][0] == "1" and results[0][1] > 0

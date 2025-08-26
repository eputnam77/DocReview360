from docreview360 import fts


def test_reindex_overwrites_document() -> None:
    """Re-indexing an existing document should replace the old entry."""
    fts.clear()
    fts.index_document("1", "first content")
    # Re-index with different content – previous behaviour produced duplicate
    # rows meaning both old and new content appeared in search results.
    fts.index_document("1", "second content")

    # The old term should no longer be searchable while the new one is.
    assert fts.search("second") == ["1"]
    assert fts.search("first") == []

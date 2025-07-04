import pytest

from docuflow import fts


def test_fts_basic_search() -> None:
    fts.clear()
    fts.index_document("a", "hello world")
    fts.index_document("b", "another doc")
    assert fts.search("hello") == ["a"]


def test_fts_invalid_input() -> None:
    fts.clear()
    with pytest.raises(ValueError):
        fts.index_document("", "x")
    with pytest.raises(ValueError):
        fts.search("")

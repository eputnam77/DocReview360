import pytest
from docreview360 import fts


def test_index_document_rejects_whitespace_id_and_content() -> None:
    with pytest.raises(ValueError):
        fts.index_document("   ", "content")
    with pytest.raises(ValueError):
        fts.index_document("id", "   ")


def test_remove_document_rejects_blank_id() -> None:
    with pytest.raises(ValueError):
        fts.remove_document("   ")

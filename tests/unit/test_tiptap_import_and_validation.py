import pytest

from docreview360 import tiptap


def test_import_tiptap_document(tmp_path):
    data = {"content": [{"type": "paragraph", "content": [{"type": "text", "text": "hi"}]}]}
    # Should create document without errors
    doc = tiptap.import_tiptap_document(data, project="p", user="u")
    assert doc.content == "hi"


def test_tiptap_invalid_content_type():
    data = {"content": [{"type": "paragraph", "content": "bad"}]}
    with pytest.raises(ValueError):
        tiptap.tiptap_to_markdown(data)

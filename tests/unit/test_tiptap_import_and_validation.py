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


def test_tiptap_invalid_part_type():
    data = {"content": [{"type": "paragraph", "content": ["bad"]}]}
    with pytest.raises(ValueError):
        tiptap.tiptap_to_markdown(data)


def test_tiptap_missing_content_key():
    with pytest.raises(ValueError):
        tiptap.tiptap_to_markdown({})


def test_tiptap_invalid_paragraph_type():
    data = {"content": [{"type": "notpara", "content": []}]}
    with pytest.raises(ValueError):
        tiptap.tiptap_to_markdown(data)


def test_markdown_to_tiptap_ignores_empty_lines():
    result = tiptap.markdown_to_tiptap("a\n\n b \n")
    assert result["type"] == "doc"
    texts = [p["content"][0]["text"].strip() for p in result["content"]]
    assert texts == ["a", "b"]


def test_tiptap_unsupported_node_type_error_message():
    data = {"type": "doc", "content": [{"type": "fancyWidget", "content": []}]}
    with pytest.raises(ValueError) as exc:
        tiptap.tiptap_to_markdown(data)
    assert "fancyWidget" in str(exc.value)


def test_tiptap_unsupported_mark_type_error_message():
    data = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": "Hello",
                        "marks": [{"type": "rainbow"}],
                    }
                ],
            }
        ],
    }
    with pytest.raises(ValueError) as exc:
        tiptap.tiptap_to_markdown(data)
    assert "rainbow" in str(exc.value)

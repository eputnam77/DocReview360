import copy

import pytest
from docreview360 import documents as doc_mod
from docreview360 import search as search_mod
from docreview360.tiptap import import_tiptap_document, tiptap_to_markdown


def _cleanup_document(doc_id: str) -> None:
    search_mod.search_index.remove_document(doc_id)
    doc_mod.documents.pop(doc_id, None)


def test_tiptap_to_markdown_supports_extended_nodes() -> None:
    data = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Styled "},
                    {
                        "type": "text",
                        "text": "segment",
                        "marks": [{"type": "bold"}, {"type": "underline"}],
                    },
                    {"type": "text", "text": " and "},
                    {
                        "type": "text",
                        "text": "docs",
                        "marks": [
                            {
                                "type": "link",
                                "attrs": {"href": "https://example.com"},
                            }
                        ],
                    },
                ],
            },
            {
                "type": "blockquote",
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Quote"}]}],
            },
            {
                "type": "codeBlock",
                "attrs": {"language": "python"},
                "content": [
                    {"type": "text", "text": "print('hi')\n"},
                ],
            },
            {"type": "horizontalRule"},
            {
                "type": "table",
                "content": [
                    {
                        "type": "tableRow",
                        "content": [
                            {
                                "type": "tableHeader",
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [{"type": "text", "text": "Name"}],
                                    }
                                ],
                            },
                            {
                                "type": "tableHeader",
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [{"type": "text", "text": "Value"}],
                                    }
                                ],
                            },
                        ],
                    },
                    {
                        "type": "tableRow",
                        "content": [
                            {
                                "type": "tableCell",
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [{"type": "text", "text": "Alpha"}],
                                    }
                                ],
                            },
                            {
                                "type": "tableCell",
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [{"type": "text", "text": "1"}],
                                    }
                                ],
                            },
                        ],
                    },
                ],
            },
        ],
    }

    markdown = tiptap_to_markdown(data)
    expected = "\n".join(
        [
            "Styled <u>**segment**</u> and [docs](https://example.com)",
            "> Quote",
            "```python",
            "print('hi')",
            "",
            "```",
            "---",
            "| Name | Value |",
            "| --- | --- |",
            "| Alpha | 1 |",
        ]
    )
    assert markdown == expected


def test_import_tiptap_document_detects_duplicates() -> None:
    data = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Duplicate"},
                ],
            }
        ],
    }

    doc = import_tiptap_document(copy.deepcopy(data))
    try:
        with pytest.raises(ValueError):
            import_tiptap_document(copy.deepcopy(data))
        linked = import_tiptap_document(copy.deepcopy(data), link_duplicates=True)
        assert linked.id == doc.id
    finally:
        _cleanup_document(doc.id)

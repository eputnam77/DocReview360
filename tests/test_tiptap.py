from docreview360.documents import get_document
from docreview360.tiptap import import_tiptap_document, markdown_to_tiptap, tiptap_to_markdown


def _cleanup_document(doc_id: str) -> None:
    from docreview360 import documents as doc_mod
    from docreview360 import search as search_mod

    search_mod.search_index.remove_document(doc_id)
    if doc_id in doc_mod.documents:
        del doc_mod.documents[doc_id]


def test_roundtrip_conversion() -> None:
    md = "Hello"
    data = markdown_to_tiptap(md)
    assert tiptap_to_markdown(data) == md


def test_import_tiptap_document() -> None:
    md = "Example"
    data = markdown_to_tiptap(md)
    doc = import_tiptap_document(data)
    try:
        assert get_document(doc.id) is doc
        assert doc.content == md
        assert doc.history[0].steps == [{"type": "tiptap_snapshot", "doc": data}]
    finally:
        _cleanup_document(doc.id)


def test_tiptap_to_markdown_with_headings_lists_and_marks() -> None:
    data = {
        "type": "doc",
        "content": [
            {
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "Overview"}],
            },
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Intro with "},
                    {
                        "type": "text",
                        "text": "style",
                        "marks": [{"type": "italic"}, {"type": "bold"}],
                    },
                ],
            },
            {
                "type": "bulletList",
                "content": [
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "First"}],
                            }
                        ],
                    },
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": "Second",
                                        "marks": [{"type": "bold"}],
                                    }
                                ],
                            }
                        ],
                    },
                ],
            },
        ],
    }

    markdown = tiptap_to_markdown(data)
    assert markdown == "## Overview\nIntro with ***style***\n- First\n- **Second**"


def test_import_tiptap_document_preserves_rich_structure() -> None:
    data = {
        "type": "doc",
        "content": [
            {
                "type": "orderedList",
                "attrs": {"start": 2},
                "content": [
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": "Alpha",
                                        "marks": [{"type": "italic"}],
                                    }
                                ],
                            }
                        ],
                    },
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": "Beta",
                                        "marks": [{"type": "bold"}],
                                    }
                                ],
                            }
                        ],
                    },
                ],
            }
        ],
    }

    doc = import_tiptap_document(data)
    try:
        expected_markdown = "2. *Alpha*\n3. **Beta**"
        assert doc.content == expected_markdown
        assert doc.history[0].steps == [{"type": "tiptap_snapshot", "doc": data}]
    finally:
        _cleanup_document(doc.id)

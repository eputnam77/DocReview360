from docreview360.documents import get_document
from docreview360.tiptap import import_tiptap_document, markdown_to_tiptap, tiptap_to_markdown


def test_roundtrip_conversion() -> None:
    md = "Hello"
    data = markdown_to_tiptap(md)
    assert tiptap_to_markdown(data) == md


def test_import_tiptap_document() -> None:
    md = "Example"
    data = markdown_to_tiptap(md)
    doc = import_tiptap_document(data)
    assert get_document(doc.id) is doc
    assert doc.content == md
    from docreview360 import documents as doc_mod
    from docreview360 import search as search_mod

    search_mod.search_index.remove_document(doc.id)
    del doc_mod.documents[doc.id]

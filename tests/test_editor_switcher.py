import pytest

from docreview360.documents import DocumentModel, import_document, set_document_editor
from docreview360.editor_switcher import render_editor


def test_render_default_editor() -> None:
    doc = DocumentModel(id="1", content="hi")
    html = render_editor(doc)
    assert "tiptap-editor" in html


def test_render_switched_editor() -> None:
    # Use import_document to properly add the document to the dictionary
    doc = import_document("test_doc.md", b"hi")

    set_document_editor(doc.id, "onlyoffice")
    html = render_editor(doc)
    assert f"onlyoffice/{doc.id}" in html

    # Cleanup to avoid side effects
    from docreview360 import documents as doc_module
    from docreview360 import search as search_module

    search_module.search_index.remove_document(doc.id)
    if doc.id in doc_module.documents:
        del doc_module.documents[doc.id]


def test_unknown_editor() -> None:
    doc = DocumentModel(id="3", content="hi", editor="bogus")
    with pytest.raises(ValueError):
        render_editor(doc)

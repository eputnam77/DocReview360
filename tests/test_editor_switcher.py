import pytest
from docreview360.documents import DocumentModel, set_document_editor
from docreview360.editor_switcher import render_editor


def test_render_default_editor() -> None:
    doc = DocumentModel(id="1", content="hi")
    html = render_editor(doc)
    assert "tiptap-editor" in html


def test_render_switched_editor() -> None:
    doc = DocumentModel(id="2", content="hi")
    from docreview360.documents import documents

    documents[doc.id] = doc
    set_document_editor(doc.id, "xml")
    html = render_editor(doc)
    assert "xml-editor" in html


def test_unknown_editor() -> None:
    doc = DocumentModel(id="3", content="hi", editor="bogus")
    with pytest.raises(ValueError):
        render_editor(doc)

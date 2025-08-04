"""MS Word upload-edit-download round-trip tests."""

from docreview360.documents import DocumentModel, import_document, update_document
from docreview360.exporter import export_document


def test_word_roundtrip_preserves_numbering_and_comments() -> None:
    source = DocumentModel(id="w1", content="1. Intro //comment")
    data, _, _ = export_document(source, "docx")
    doc = import_document("w1.docx", data)
    assert "1. Intro" in doc.content and "comment" in doc.content

    update_document(doc.id, doc.content + "\n2. More")
    data2, _, _ = export_document(doc, "docx")
    doc2 = import_document("w2.docx", data2)
    assert "1. Intro" in doc2.content
    assert "2. More" in doc2.content
    assert "comment" in doc2.content

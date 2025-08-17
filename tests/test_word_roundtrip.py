"""MS Word upload-edit-download round-trip tests."""

from docreview360.documents import DocumentModel, import_document, update_document
from docreview360.exporter import export_document


def test_word_roundtrip_preserves_headings_and_tracked_changes() -> None:
    source = DocumentModel(id="w1", content="# Intro\n[DEL:old]\n[INS:new]")
    data, _, _ = export_document(source, "docx")
    doc = import_document("w1.docx", data)
    assert "# Intro" in doc.content
    assert "[DEL:old]" in doc.content
    assert "[INS:new]" in doc.content

    update_document(doc.id, doc.content + "\n## More")
    data2, _, _ = export_document(doc, "docx")
    doc2 = import_document("w2.docx", data2)
    assert "# Intro" in doc2.content
    assert "## More" in doc2.content
    assert "[DEL:old]" in doc2.content
    assert "[INS:new]" in doc2.content

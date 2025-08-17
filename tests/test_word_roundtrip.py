"""MS Word upload-edit-download round-trip tests."""

from docreview360.documents import DocumentModel, import_document, update_document
from docreview360.exporter import export_document
from docreview360.tiptap import import_tiptap_document, markdown_to_tiptap


def test_word_roundtrip_preserves_headings_styles_and_tracked_changes() -> None:
    source = DocumentModel(
        id="w1",
        content="# Intro\nThis has **bold** and *italic* text.\n[DEL:old]\n[INS:new]",
    )
    data, _, _ = export_document(source, "docx")
    doc = import_document("w1.docx", data)

    assert doc.content.startswith("# Intro")
    assert "**bold**" in doc.content
    assert "*italic*" in doc.content
    assert "[DEL:old]" in doc.content
    assert "[INS:new]" in doc.content

    update_document(doc.id, doc.content + "\n## More")
    data2, _, _ = export_document(doc, "docx")
    doc2 = import_document("w2.docx", data2)
    assert doc2.content.startswith("# Intro")
    assert "## More" in doc2.content
    assert "**bold**" in doc2.content
    assert "*italic*" in doc2.content
    assert "[DEL:old]" in doc2.content
    assert "[INS:new]" in doc2.content


def test_word_tiptap_word_cycle_with_complex_formatting() -> None:
    source = DocumentModel(
        id="wcycle",
        content=(
            "# Heading 1\n"
            "Paragraph with **bold** and *italic*.\n"
            "[INS:added]\n"
            "[DEL:removed]\n"
            "## Heading 2"
        ),
    )
    # Word -> Document
    word_bytes, _, _ = export_document(source, "docx")
    doc_from_word = import_document("cycle1.docx", word_bytes)

    # Document -> TipTap -> Document
    tiptap_json = markdown_to_tiptap(doc_from_word.content)
    doc_from_tiptap = import_tiptap_document(tiptap_json)

    # Document -> Word -> Document
    word_bytes2, _, _ = export_document(doc_from_tiptap, "docx")
    roundtrip = import_document("cycle2.docx", word_bytes2)

    assert roundtrip.content == doc_from_word.content
    assert "# Heading 1" in roundtrip.content
    assert "## Heading 2" in roundtrip.content
    assert "**bold**" in roundtrip.content
    assert "*italic*" in roundtrip.content
    assert "[INS:added]" in roundtrip.content
    assert "[DEL:removed]" in roundtrip.content

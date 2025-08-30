from docreview360.documents import DocumentModel
from docreview360.exporter import preview_document


def test_preview_document_json_uses_exported_text() -> None:
    doc = DocumentModel(id="1", content="hello")
    preview = preview_document(doc, "json")
    assert preview.startswith('{"id":"1"')

from docreview360.doc_types import document_types


def test_sample_document_type_exists() -> None:
    assert "sample" in document_types
    doc = document_types["sample"]
    assert doc.template.startswith("<h1>")

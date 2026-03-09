from pathlib import Path

from docreview360.document_converter import convert_document


def test_task223_convert_document() -> None:
    """DOCX files can be converted to PDF or HTML."""
    convert_document(Path("sample.docx"), "pdf")

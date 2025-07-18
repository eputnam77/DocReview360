from pathlib import Path

from docreview360.stubs.task223 import convert_document


def test_task223_convert_document() -> None:
    """DOCX files can be converted to PDF or HTML."""
    convert_document(Path("sample.docx"), "pdf")

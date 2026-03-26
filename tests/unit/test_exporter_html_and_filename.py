import json

import pytest
from docreview360.exporter import export_document


class DummyDoc:
    def __init__(self, doc_id: str, content: str, number: int | None = None) -> None:
        self.id = doc_id
        self.content = content
        self.number = number

    def model_dump_json(self) -> str:
        return json.dumps({"id": self.id, "content": self.content, "number": self.number})


def test_html_export_escapes_content() -> None:
    doc = DummyDoc("1", "<b>bold</b>")
    data, media, name = export_document(doc, "html")
    assert media == "text/html"
    assert b"&lt;b&gt;bold&lt;/b&gt;" in data
    assert name == "1.html"


def test_filename_sanitizes_newlines() -> None:
    doc = DummyDoc("evil\nid", "content")
    _, _, name = export_document(doc, "markdown")
    assert name == "evil_id.md"


def test_export_document_requires_string_format() -> None:
    doc = DummyDoc("1", "content")
    with pytest.raises(TypeError) as excinfo:
        export_document(doc, fmt=123)  # type: ignore[arg-type]
    assert "fmt must be a string" in str(excinfo.value)

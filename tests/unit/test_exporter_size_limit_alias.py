import pytest

from docreview360 import exporter


class DummyDoc:
    def __init__(self, doc_id: str, content: str, number: int | None = None) -> None:
        self.id = doc_id
        self.content = content
        self.number = number

    def model_dump_json(self) -> str:
        return "{}"


def test_export_size_limit_applies_to_markdown_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        exporter,
        "load_settings",
        lambda: {"exports": {"size_limits": {"md": 5}}},
    )
    doc = DummyDoc("doc-1", "hello world")
    with pytest.raises(exporter.ExportSizeLimitError) as excinfo:
        exporter.export_document(doc, "markdown")
    assert excinfo.value.format == "markdown"

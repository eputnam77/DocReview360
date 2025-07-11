import pytest

from docreview360.documents import DocumentModel
from docreview360.exporter import export_document, set_guardrails


def test_guardrails_block_export() -> None:
    def check(content: str) -> bool:
        return "PII" in content

    set_guardrails(check)
    doc = DocumentModel(id="1", content="contains PII", history=[])
    with pytest.raises(ValueError):
        export_document(doc, "pdf")

    set_guardrails(None)
    data, media, name = export_document(doc, "pdf")
    assert media == "application/pdf"

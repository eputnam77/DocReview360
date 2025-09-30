import pytest

from docreview360.documents import DocumentModel
from docreview360 import exporter


@pytest.fixture
def sample_document() -> DocumentModel:
    return DocumentModel(id="doc-1", content="Hello world", history=[])


def test_docx_export_enforces_size_limit(
    monkeypatch: pytest.MonkeyPatch, sample_document: DocumentModel
) -> None:
    events: list[tuple[tuple, dict]] = []

    monkeypatch.setattr(
        exporter,
        "load_settings",
        lambda: {"exports": {"size_limits": {"docx": 512}}},
    )
    monkeypatch.setattr(exporter, "log_event", lambda *a, **kw: events.append((a, kw)))

    with pytest.raises(exporter.ExportSizeLimitError) as exc:
        exporter.export_document(sample_document, "docx")

    assert exc.value.document_id == sample_document.id
    assert exc.value.format == "docx"
    assert events and events[0][0][0] == "export_size_limit_exceeded"
    assert events[0][1]["fmt"] == "docx"


def test_pdf_export_enforces_size_limit(
    monkeypatch: pytest.MonkeyPatch, sample_document: DocumentModel
) -> None:
    events: list[tuple[tuple, dict]] = []

    monkeypatch.setattr(
        exporter,
        "load_settings",
        lambda: {"exports": {"size_limits": {"pdf": 10}}},
    )
    monkeypatch.setattr(exporter, "log_event", lambda *a, **kw: events.append((a, kw)))

    with pytest.raises(exporter.ExportSizeLimitError) as exc:
        exporter.export_document(sample_document, "pdf")

    assert exc.value.document_id == sample_document.id
    assert exc.value.format == "pdf"
    assert events and events[0][0][0] == "export_size_limit_exceeded"
    assert events[0][1]["fmt"] == "pdf"


def test_export_batch_reports_offending_document(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[tuple[tuple, dict]] = []

    monkeypatch.setattr(
        exporter,
        "load_settings",
        lambda: {"exports": {"size_limits": {"pdf": 90}}},
    )
    monkeypatch.setattr(exporter, "log_event", lambda *a, **kw: events.append((a, kw)))

    doc1 = DocumentModel(id="batch-1", content="First", history=[])
    doc2 = DocumentModel(id="batch-2", content="Second", history=[])

    with pytest.raises(exporter.ExportSizeLimitError) as exc:
        exporter.export_batch([doc1, doc2], "pdf")

    assert exc.value.document_id == doc2.id
    assert events and events[-1][1]["fmt"] == "pdf"

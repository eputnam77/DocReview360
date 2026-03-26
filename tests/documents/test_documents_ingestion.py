import pytest
from docreview360 import documents, fts, search


@pytest.fixture(autouse=True)
def reset_document_state() -> None:
    original_pipelines = documents.ingestion_registry.items()
    documents.documents.clear()
    documents._re_review.clear()
    documents._project_document_numbers.clear()
    documents._next_document_number = 1
    fts.clear()
    search.search_index.index.clear()
    yield
    documents.documents.clear()
    documents._re_review.clear()
    documents._project_document_numbers.clear()
    documents._next_document_number = 1
    fts.clear()
    search.search_index.index.clear()
    current = documents.ingestion_registry.items()
    for mime in current:
        documents.unregister_ingestion_pipeline(mime)
    for mime, pipeline in original_pipelines.items():
        documents.register_ingestion_pipeline(mime, pipeline)


def test_default_allows_pdf() -> None:
    assert "application/pdf" in documents.DEFAULT_ALLOWED_MIME_TYPES


def test_pdf_ingestion_sanitises_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "docreview360.documents._store.load_settings",
        lambda: {"documents": {"enable_pdf_ingestion": True}},
    )

    calls: list[bytes] = []

    def fake_extract(data: bytes) -> str:
        calls.append(data)
        return "Hello <script>alert(1)</script>"

    monkeypatch.setattr("docreview360.documents._store._extract_pdf_text", fake_extract)

    doc = documents.import_document("sample.pdf", b"%PDF-1.4 fake content")

    assert calls, "expected default PDF pipeline to invoke the extractor"
    assert "alert" not in doc.content
    assert "Hello" in doc.content


def test_custom_pdf_pipeline_is_invoked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "docreview360.documents._store.load_settings",
        lambda: {"documents": {"enable_pdf_ingestion": True}},
    )

    invoked: list[str] = []

    def custom_pipeline(data: bytes, filename: str) -> str:
        invoked.append(filename)
        return "custom output"

    documents.register_ingestion_pipeline("application/pdf", custom_pipeline)

    doc = documents.import_document("custom.pdf", b"%PDF-1.7 content")

    assert invoked == ["custom.pdf"], "custom pipeline should handle the ingestion"
    assert doc.content == "custom output"


def test_pdf_ingestion_rejected_without_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("docreview360.documents._store.load_settings", lambda: {"documents": {}})

    with pytest.raises(ValueError) as exc:
        documents.import_document("disabled.pdf", b"%PDF-no-pipeline")

    assert "no PDF ingestion pipeline" in str(exc.value)

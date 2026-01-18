import pytest

import docreview360.documents as doc_mod
from docreview360.documents import DocumentModel, import_document
from docreview360.exporter import export_document


@pytest.fixture(autouse=True)
def clear_documents():
    doc_mod.documents.clear()
    yield
    doc_mod.documents.clear()


def test_import_document_sanitizes_html_content():
    payload = b"<h1>Safe</h1><script>alert('x')</script>"
    doc = import_document("danger.html", payload)
    assert "<script" not in doc.content.lower()
    assert doc.content == "<h1>Safe</h1>"
    assert doc_mod.documents[doc.id].content == doc.content


def test_import_document_respects_size_limit(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        doc_mod,
        "load_settings",
        lambda: {"documents": {"max_upload_size": 4}},
    )
    with pytest.raises(ValueError, match="size limit"):
        import_document("too-big.md", b"ABCDE")


def test_import_document_rejects_unsupported_mime(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(doc_mod, "load_settings", lambda: {})
    png_bytes = b"\x89PNG\r\n\x1a\n" + b"0" * 10
    with pytest.raises(ValueError, match="unsupported MIME type"):
        import_document("image.png", png_bytes)


def test_export_resanitizes_and_blocks_unsanitized_documents():
    doc = DocumentModel(id="bad", content="<script>boom()</script>", history=[])
    with pytest.raises(ValueError, match="guardrails"):
        export_document(doc, "markdown")

    clean_doc = import_document("clean.md", b"# Title\n<script>alert('x')</script>")
    md_bytes, media, _ = export_document(clean_doc, "markdown")
    assert media == "text/markdown"
    assert b"<script" not in md_bytes.lower()

    html_bytes, html_media, _ = export_document(clean_doc, "html")
    assert html_media == "text/html"
    assert b"<script" not in html_bytes.lower()

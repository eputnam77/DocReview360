from docreview360 import documents, fts


def test_update_document_sanitizes_content() -> None:
    documents.documents.clear()
    fts.clear()
    doc = documents.import_document("note.txt", b"hello")

    updated, _ = documents.update_document(doc.id, "<script>alert(1)</script>Hi")

    assert "script" not in updated.content.lower()
    assert "alert" not in updated.content.lower()
    assert "Hi" in updated.content


def test_update_document_skips_fts_on_blank_content(monkeypatch) -> None:
    documents.documents.clear()
    fts.clear()
    doc = documents.import_document("note.txt", b"hello")

    def _raise_if_called(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("fts.index_document should not be called for blank content")

    monkeypatch.setattr(fts, "index_document", _raise_if_called)

    updated, _ = documents.update_document(doc.id, "   ")

    assert updated.content.strip() == ""

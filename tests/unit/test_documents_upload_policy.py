import pytest

import docreview360.documents as documents


@pytest.fixture(autouse=True)
def clear_documents() -> None:
    documents.documents.clear()
    yield
    documents.documents.clear()


def test_import_document_negative_size_limit_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys
    monkeypatch.setattr(
        sys.modules["docreview360.documents._store"],
        "load_settings",
        lambda: {"documents": {"max_upload_size": -10}},
    )
    doc = documents.import_document("note.txt", b"hello")
    assert doc.content == "hello"

import sys
from types import SimpleNamespace

import pytest

import docreview360.documents as doc_mod
from docreview360.documents import import_document


@pytest.fixture(autouse=True)
def clear_documents():
    doc_mod.documents.clear()
    yield
    doc_mod.documents.clear()


def test_import_document_accepts_case_insensitive_allowed_mime_types(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sys.modules["docreview360.documents._store"],
        "load_settings",
        lambda: {
            "documents": {
                "allowed_mime_types": [" TEXT/PLAIN ", "TEXT/MARKDOWN"],
            }
        },
    )

    doc_txt = import_document("note.txt", b"hello")
    doc_md = import_document("note.md", b"# heading")

    assert doc_txt.id in doc_mod.documents
    assert doc_md.id in doc_mod.documents


def test_import_document_strips_charset_from_magic_detection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeMagic:
        def __init__(self, mime: bool = True) -> None:
            self.mime = mime

        def from_buffer(self, data: bytes) -> str:
            return "TEXT/PLAIN; charset=utf-8"

    monkeypatch.setitem(sys.modules, "magic", SimpleNamespace(Magic=FakeMagic))
    monkeypatch.setattr(
        sys.modules["docreview360.documents._store"],
        "load_settings",
        lambda: {"documents": {"allowed_mime_types": ["text/plain"]}},
    )

    doc = import_document("note.bin", b"hello from magic")

    assert doc.id in doc_mod.documents

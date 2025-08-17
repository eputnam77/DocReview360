"""Editor autosave tests."""

import time

from docreview360.documents import autosave_document, import_document, get_document_versions


def test_autosave_debounced_patch_updates_within_5s() -> None:
    doc = import_document("auto.md", b"start")
    start = time.monotonic()
    autosave_document(doc.id, "update")
    elapsed = time.monotonic() - start
    assert elapsed < 5
    assert doc.content == "update"
    assert get_document_versions(doc.id) == ["start", "update"]
    autosave_document(doc.id, "update")
    assert get_document_versions(doc.id) == ["start", "update"]

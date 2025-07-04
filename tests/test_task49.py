from docuflow.documents import import_document, needs_rereview
from docuflow.stubs.task49 import task49


def test_major_edit_triggers_rereview() -> None:
    doc = import_document("a.txt", b"hello world")
    assert not needs_rereview(doc.id)
    assert task49(doc.id, "completely different content") is True
    assert needs_rereview(doc.id)

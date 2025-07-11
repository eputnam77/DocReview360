from docreview360.documents import DocumentModel
from docreview360.stubs.task27 import task27, task27_preview


def test_task27_batch_export_and_preview() -> None:
    docs = [
        DocumentModel(id="d1", content="one"),
        DocumentModel(id="d2", content="two"),
    ]
    archive = task27(docs, "markdown")
    assert archive.startswith(b"PK")  # zip signature
    preview = task27_preview(docs[0], "markdown", length=2)
    assert preview == "on"

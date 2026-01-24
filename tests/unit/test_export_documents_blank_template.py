from io import BytesIO
from zipfile import ZipFile

from docreview360 import celery_app
from docreview360.config import Config
from docreview360.documents import document_lock, documents, import_document


def test_export_documents_uses_default_template_when_blank(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "docreview360.yaml"
    cfg = Config(
        database="sqlite",
        editor="tiptap",
        cms="none",
        auth="oidc",
        filename_template="  ",
    )
    cfg.save(config_path)
    monkeypatch.setattr(celery_app, "CONFIG_FILE", config_path)

    doc = import_document("sample.txt", b"Hello world")
    try:
        data = celery_app.export_documents([doc.id], "markdown")
    finally:
        with document_lock:
            documents.clear()

    with ZipFile(BytesIO(data)) as zf:
        assert zf.namelist() == [f"{doc.id}.md"]

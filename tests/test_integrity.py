import hashlib

from docreview360.config import Config
from docreview360.documents import DocumentModel, documents
from docreview360.integrity import verify_integrity
from docreview360.logs import clear_logs, logs


def test_integrity_mismatch_triggers_log(monkeypatch) -> None:
    backup = documents.copy()
    documents.clear()
    try:
        data = b"original"
        digest = hashlib.sha256(data).hexdigest()
        doc = DocumentModel(id="1", content="original", ingestion_hash=digest)
        documents[doc.id] = doc

        monkeypatch.setattr(
            Config,
            "load",
            lambda path: Config(database="db", editor="ed", cms="sharepoint", auth="none"),
        )

        class Dummy:
            def download_file(self, item_id: str) -> bytes:
                return b"tampered"

        monkeypatch.setattr("docreview360.integrity._client_from_env", lambda: Dummy())

        clear_logs()
        mismatches = verify_integrity()
        assert mismatches == [doc.id]
        assert any(
            entry.action == "integrity_mismatch" and entry.context["document"] == doc.id
            for entry in logs
        )
    finally:
        documents.clear()
        documents.update(backup)

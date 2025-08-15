import pytest

import docreview360.api as api
from docreview360.config import Config
from docreview360.documents import import_document, documents
from docreview360.logs import clear_logs, logs


@pytest.mark.asyncio
async def test_read_logging_toggle(monkeypatch):
    documents.clear()
    doc = import_document("a.txt", b"hello")
    clear_logs()

    def load_true(cls, path=api.CONFIG_FILE):
        return Config(database="sqlite", editor="tiptap", cms="none", auth="none", log_reads=True)

    def load_false(cls, path=api.CONFIG_FILE):
        return Config(database="sqlite", editor="tiptap", cms="none", auth="none", log_reads=False)

    monkeypatch.setattr(api.Config, "load", classmethod(load_true))
    await api.get_document_endpoint(doc.id)
    assert any(e.action == "read" and e.entity_id == doc.id for e in logs)

    clear_logs()
    monkeypatch.setattr(api.Config, "load", classmethod(load_false))
    await api.get_document_endpoint(doc.id)
    assert not any(e.action == "read" and e.entity_id == doc.id for e in logs)

import pytest

import docreview360.api as api
import docreview360.graphql_api as gql
from docreview360.config import Config
from docreview360.documents import documents, import_document
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


def test_graphql_read_logging(monkeypatch):
    documents.clear()
    import_document("a.txt", b"hello")
    clear_logs()

    def load_true(cls, path=gql.CONFIG_FILE):
        return Config(database="sqlite", editor="tiptap", cms="none", auth="none", log_reads=True)

    def load_false(cls, path=gql.CONFIG_FILE):
        return Config(database="sqlite", editor="tiptap", cms="none", auth="none", log_reads=False)

    query = "{ documents { id content } }"

    monkeypatch.setattr(gql.Config, "load", classmethod(load_true))
    gql.execute_query(query)
    assert any(e.action == "read" and e.entity_id == "graphql" for e in logs)

    clear_logs()
    monkeypatch.setattr(gql.Config, "load", classmethod(load_false))
    gql.execute_query(query)
    assert not any(e.action == "read" and e.entity_id == "graphql" for e in logs)

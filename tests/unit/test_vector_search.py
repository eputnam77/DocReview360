import types
import pytest
from docreview360 import vector_search as vs


def dummy_response(data=None):
    class Resp:
        def __init__(self, data):
            self._data = data or {}

        def raise_for_status(self):
            pass

        def json(self):
            return self._data

    return Resp(data)


def test_index_document_replaces_previous(monkeypatch):
    vs.clear()
    vs.index_document("1", "foo bar")
    assert vs._doc_freq["foo"] == 1 and vs._doc_freq["bar"] == 1
    vs.index_document("1", "foo baz")
    assert vs._doc_freq.get("bar", 0) == 0
    assert vs._doc_freq["foo"] == 1
    assert vs._doc_freq["baz"] == 1


def test_index_document_remote(monkeypatch):
    vs.clear()
    calls = []
    monkeypatch.setenv("OPENSEARCH_URL", "http://os")
    monkeypatch.setenv("PGVECTOR_URL", "http://pg")
    monkeypatch.setattr(vs, "OPENSEARCH_URL", "http://os")
    monkeypatch.setattr(vs, "PGVECTOR_URL", "http://pg")
    monkeypatch.setattr(
        vs.httpx, "put", lambda *a, **k: calls.append(("put", a, k)) or dummy_response()
    )
    monkeypatch.setattr(
        vs.httpx, "post", lambda *a, **k: calls.append(("post", a, k)) or dummy_response()
    )
    vs.index_document("1", "foo")
    assert any(c[0] == "put" for c in calls)
    assert any(c[0] == "post" for c in calls)


def test_index_document_errors(monkeypatch):
    vs.clear()
    monkeypatch.setattr(vs, "OPENSEARCH_URL", "http://os")
    monkeypatch.setattr(vs, "PGVECTOR_URL", "http://pg")

    def bad_put(*a, **k):
        raise vs.httpx.HTTPError("boom")

    def bad_post(*a, **k):
        raise vs.httpx.HTTPError("boom")

    monkeypatch.setattr(vs.httpx, "put", bad_put)
    monkeypatch.setattr(vs.httpx, "post", bad_post)

    with pytest.raises(RuntimeError):
        vs.index_document("id", "content")


def test_search_remote_opensearch(monkeypatch):
    vs.clear()
    monkeypatch.setenv("OPENSEARCH_URL", "http://os")
    monkeypatch.setattr(vs, "OPENSEARCH_URL", "http://os")
    monkeypatch.setattr(
        vs.httpx,
        "post",
        lambda *a, **k: dummy_response({"hits": {"hits": [{"_id": "1", "_score": 1.2}]}}),
    )
    assert vs.search("query", top_k=1) == [("1", 1.2)]


def test_search_remote_opensearch_error(monkeypatch):
    vs.clear()
    monkeypatch.setattr(vs, "OPENSEARCH_URL", "http://os")
    monkeypatch.setattr(
        vs.httpx, "post", lambda *a, **k: (_ for _ in ()).throw(vs.httpx.HTTPError("bad"))
    )
    with pytest.raises(RuntimeError):
        vs.search("q")


def test_search_remote_pgvector(monkeypatch):
    vs.clear()
    monkeypatch.setenv("OPENSEARCH_URL", "")
    monkeypatch.setenv("PGVECTOR_URL", "http://pg")
    monkeypatch.setattr(vs, "OPENSEARCH_URL", "")
    monkeypatch.setattr(vs, "PGVECTOR_URL", "http://pg")
    monkeypatch.setattr(
        vs.httpx, "post", lambda *a, **k: dummy_response({"results": [{"id": "1", "score": 0.5}]})
    )
    assert vs.search("query", top_k=1) == [("1", 0.5)]


def test_search_remote_pgvector_error(monkeypatch):
    vs.clear()
    monkeypatch.setattr(vs, "OPENSEARCH_URL", "")
    monkeypatch.setattr(vs, "PGVECTOR_URL", "http://pg")
    monkeypatch.setattr(
        vs.httpx, "post", lambda *a, **k: (_ for _ in ()).throw(vs.httpx.HTTPError("bad"))
    )
    with pytest.raises(RuntimeError):
        vs.search("q")


def test_search_local(monkeypatch):
    vs.clear()
    monkeypatch.setattr(vs, "OPENSEARCH_URL", "")
    monkeypatch.setattr(vs, "PGVECTOR_URL", "")
    vs.index_document("1", "alpha beta")
    vs.index_document("2", "alpha gamma")
    results = vs.search("beta", top_k=2)
    assert results[0][0] == "1"


def test_empty_query_raises():
    with pytest.raises(ValueError):
        vs.search("   ")


def test_cosine_zero():
    assert vs._cosine([0], [1]) == 0.0


def test_index_document_empty():
    vs.clear()
    with pytest.raises(ValueError):
        vs.index_document("", "")


def test_index_document_pgvector_error(monkeypatch):
    vs.clear()
    monkeypatch.setattr(vs, "OPENSEARCH_URL", "")
    monkeypatch.setattr(vs, "PGVECTOR_URL", "http://pg")
    monkeypatch.setattr(
        vs.httpx, "post", lambda *a, **k: (_ for _ in ()).throw(vs.httpx.HTTPError("bad"))
    )
    with pytest.raises(RuntimeError):
        vs.index_document("1", "content")


def test_search_top_k_positive(monkeypatch):
    vs.clear()
    monkeypatch.setattr(vs, "OPENSEARCH_URL", "")
    monkeypatch.setattr(vs, "PGVECTOR_URL", "")
    vs.index_document("1", "alpha")
    with pytest.raises(ValueError):
        vs.search("alpha", top_k=0)

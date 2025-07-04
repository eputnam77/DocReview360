import httpx
import pytest

from docuflow import vector_search


def test_vector_search_ranking() -> None:
    vector_search.clear()
    vector_search.index_document("a", "alpha beta")
    vector_search.index_document("b", "beta gamma")
    results = vector_search.search("alpha")
    assert results[0][0] == "a"

    vector_search.clear()
    assert vector_search.search("alpha") == []


def test_vector_search_invalid() -> None:
    vector_search.clear()
    with pytest.raises(ValueError):
        vector_search.index_document("", "x")
    with pytest.raises(ValueError):
        vector_search.search(" ")


def test_vector_search_opensearch_fallback(monkeypatch) -> None:
    calls = []

    def fake_post(*args, **kwargs):
        calls.append((args, kwargs))
        raise httpx.HTTPError("fail")

    monkeypatch.setenv("OPENSEARCH_URL", "http://os")
    monkeypatch.setattr(vector_search, "OPENSEARCH_URL", "http://os")
    monkeypatch.setattr(httpx, "post", fake_post)

    class Dummy:
        def raise_for_status(self) -> None:  # pragma: no cover - no-op
            pass

    monkeypatch.setattr(httpx, "put", lambda *a, **k: Dummy())

    vector_search.clear()
    vector_search.index_document("a", "alpha beta")
    with pytest.raises(RuntimeError):
        vector_search.search("alpha")
    assert calls  # ensure HTTP attempted


def test_vector_search_index_opensearch(monkeypatch) -> None:
    calls = []

    def fake_put(*args, **kwargs):
        calls.append((args, kwargs))
        raise httpx.HTTPError("fail")

    monkeypatch.setenv("OPENSEARCH_URL", "http://os")
    monkeypatch.setattr(vector_search, "OPENSEARCH_URL", "http://os")
    monkeypatch.setattr(httpx, "put", fake_put)

    vector_search.clear()
    with pytest.raises(RuntimeError):
        vector_search.index_document("a", "alpha beta")
    assert calls

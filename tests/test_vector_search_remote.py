import httpx
import pytest

from docreview360 import vector_search


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


def test_vector_search_opensearch_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def fake_post(*args: object, **kwargs: object) -> None:
        calls.append((args, kwargs))
        raise httpx.HTTPError("fail")

    monkeypatch.setenv("OPENSEARCH_URL", "http://os")
    monkeypatch.setattr(vector_search, "OPENSEARCH_URL", "http://os")
    monkeypatch.setattr(vector_search._http_client, "post", fake_post)

    class Dummy:
        def raise_for_status(self) -> None:
            pass

    def fake_put(*args: object, **kwargs: object) -> Dummy:
        return Dummy()

    monkeypatch.setattr(vector_search._http_client, "put", fake_put)

    vector_search.clear()
    vector_search.index_document("a", "alpha beta")
    with pytest.raises(RuntimeError):
        vector_search.search("alpha")
    assert calls  # ensure HTTP attempted


def test_vector_search_index_opensearch(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def fake_put(*args: object, **kwargs: object) -> None:
        calls.append((args, kwargs))
        raise httpx.HTTPError("fail")

    monkeypatch.setenv("OPENSEARCH_URL", "http://os")
    monkeypatch.setattr(vector_search, "OPENSEARCH_URL", "http://os")
    monkeypatch.setattr(vector_search._http_client, "put", fake_put)

    vector_search.clear()
    with pytest.raises(RuntimeError):
        vector_search.index_document("a", "alpha beta")
    assert calls


def test_vector_search_opensearch_success(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(
        url: str, json: dict[str, object], timeout: int | None = None
    ) -> httpx.Response:
        assert url.endswith("/_search")
        data = {"hits": {"hits": [{"_id": "a", "_score": 1.0}]}}
        req = httpx.Request("POST", url)
        return httpx.Response(200, json=data, request=req)

    def fake_put(
        url: str, json: dict[str, object], timeout: int | None = None
    ) -> httpx.Response:
        req = httpx.Request("PUT", url)
        return httpx.Response(201, request=req)

    monkeypatch.setenv("OPENSEARCH_URL", "http://os")
    monkeypatch.setattr(vector_search, "OPENSEARCH_URL", "http://os")
    monkeypatch.setattr(vector_search._http_client, "post", fake_post)
    monkeypatch.setattr(vector_search._http_client, "put", fake_put)

    vector_search.clear()
    vector_search.index_document("a", "alpha beta")
    res = vector_search.search("alpha")
    assert res == [("a", 1.0)]


def test_vector_search_pgvector(monkeypatch: pytest.MonkeyPatch) -> None:
    idx_calls: list[tuple[object, ...]] = []
    search_calls: list[tuple[object, ...]] = []

    def fake_post_index(
        url: str, json: dict[str, object], timeout: int | None = None
    ) -> httpx.Response:
        idx_calls.append((url, json))
        req = httpx.Request("POST", url)
        return httpx.Response(201, request=req)

    def fake_post_search(
        url: str, json: dict[str, object], timeout: int | None = None
    ) -> httpx.Response:
        search_calls.append((url, json))
        data = {"results": [{"id": "a", "score": 0.9}]}
        req = httpx.Request("POST", url)
        return httpx.Response(200, json=data, request=req)

    monkeypatch.delenv("OPENSEARCH_URL", raising=False)
    monkeypatch.setattr(vector_search, "OPENSEARCH_URL", None)
    monkeypatch.setenv("PGVECTOR_URL", "http://pgv")
    monkeypatch.setattr(vector_search, "PGVECTOR_URL", "http://pgv")

    def route_post(
        url: str, json: dict[str, object], timeout: int | None = None
    ) -> httpx.Response:
        if url.endswith("/index"):
            return fake_post_index(url, json, timeout)
        return fake_post_search(url, json, timeout)

    monkeypatch.setattr(vector_search._http_client, "post", route_post)

    vector_search.clear()
    vector_search.index_document("a", "alpha beta")
    res = vector_search.search("alpha")
    assert res == [("a", 0.9)]
    assert idx_calls and search_calls

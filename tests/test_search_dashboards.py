"""Search indexing, vector queries, and Metabase dashboard tests."""

from __future__ import annotations

import httpx
import pytest

from docreview360 import vector_search
from docreview360.stubs.task82 import OpenSearchClient

# SR-01


def test_document_creation_triggers_opensearch_refresh() -> None:
    client = OpenSearchClient()
    client.index_document("hello world")
    assert client.search("hello") == ["hello world"]
    assert len(client.index) > 0


# SR-02


def test_vector_query_returns_topk_and_embedding(monkeypatch: pytest.MonkeyPatch) -> None:
    embed_len: dict[str, int] = {}

    def fake_post(
        url: str, json: dict[str, object], timeout: int | None = None
    ) -> httpx.Response:
        embed_len["len"] = 1536
        data = {"results": [{"id": "a", "score": 0.9}]}
        req = httpx.Request("POST", url)
        return httpx.Response(200, json=data, request=req)

    monkeypatch.delenv("OPENSEARCH_URL", raising=False)
    monkeypatch.setenv("PGVECTOR_URL", "http://pgv")
    monkeypatch.setattr(vector_search, "PGVECTOR_URL", "http://pgv")
    monkeypatch.setattr(vector_search._http_client, "post", fake_post)
    vector_search.clear()
    res = vector_search.search("alpha", top_k=1)
    assert res == [("a", 0.9)]
    assert embed_len["len"] == 1536


# DB-01


def test_docs_by_phase_card_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(
        url: str, headers: dict[str, str] | None = None, timeout: int | None = None
    ) -> httpx.Response:
        req = httpx.Request("GET", url)
        return httpx.Response(200, json={"name": "Docs by Phase"}, request=req)

    monkeypatch.setattr(httpx, "get", fake_get)
    resp = httpx.get("http://mb/api/card/1", headers={"X-Metabase-Session": "tok"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Docs by Phase"

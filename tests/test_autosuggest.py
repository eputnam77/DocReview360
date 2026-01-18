import httpx
import pytest

from docreview360.autosuggest import Suggestion, suggest


@pytest.mark.asyncio
async def test_suggest_parses_response(monkeypatch):
    """Response JSON should be parsed under the named suggestion key."""

    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover - simple stub
        assert request.url.path == "/docs/_suggest"
        return httpx.Response(
            200, json={"suggest": {"simple": [{"options": [{"text": "foo", "_score": 1.23}]}]}}
        )

    transport = httpx.MockTransport(handler)
    real_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        return real_client(transport=transport)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)

    suggestions = await suggest("http://example.com", "foo", index="docs")
    assert suggestions == [Suggestion(text="foo", score=1.23)]


@pytest.mark.asyncio
async def test_suggest_rejects_empty_text():
    with pytest.raises(ValueError):
        await suggest("http://example.com", "")

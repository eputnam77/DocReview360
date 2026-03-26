import docreview360.autosuggest as autosuggest
import pytest


class DummyResp:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


class DummyClient:
    def __init__(self, resp):
        self._resp = resp

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json, timeout):  # pragma: no cover - called
        return self._resp


@pytest.mark.asyncio
async def test_suggest_handles_empty_results(monkeypatch):
    resp = DummyResp({"suggest": {"simple": []}})
    monkeypatch.setattr(autosuggest.httpx, "AsyncClient", lambda: DummyClient(resp))
    # Should not raise IndexError when no suggestions are returned
    result = await autosuggest.suggest("http://os", "query")
    assert result == []


@pytest.mark.asyncio
async def test_suggest_raises_on_empty_text():
    with pytest.raises(ValueError):
        await autosuggest.suggest("http://os", "")


@pytest.mark.asyncio
async def test_suggest_returns_options(monkeypatch):
    resp = DummyResp({"suggest": {"simple": [{"options": [{"text": "hi", "_score": 0.5}]}]}})
    monkeypatch.setattr(autosuggest.httpx, "AsyncClient", lambda: DummyClient(resp))
    result = await autosuggest.suggest("http://os", "q")
    assert result == [autosuggest.Suggestion(text="hi", score=0.5)]

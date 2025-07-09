import pytest
from fastapi.testclient import TestClient

from docuflow import ai_assist
from docuflow.api import app


@pytest.mark.asyncio
async def test_ai_rewrite_endpoint(monkeypatch) -> None:
    async def fake_call(text: str) -> str:
        return "rewritten"

    from docuflow import api

    monkeypatch.setattr(api, "rewrite_text", fake_call)
    client = TestClient(app)
    resp = client.post("/ai/rewrite", json={"text": "hello"})
    assert resp.status_code == 200
    assert resp.json()["result"] == "rewritten"


@pytest.mark.asyncio
async def test_ai_summarize_endpoint(monkeypatch) -> None:
    async def fake_sum(text: str) -> str:
        return "summary"

    from docuflow import api

    monkeypatch.setattr(api, "summarize_text", fake_sum)
    client = TestClient(app)
    resp = client.post("/ai/summarize", json={"text": "some text"})
    assert resp.status_code == 200
    assert resp.json()["result"] == "summary"


@pytest.mark.asyncio
async def test_call_openai_fallback() -> None:
    result = await ai_assist._call_openai("hello world")
    assert result == "world hello"


@pytest.mark.asyncio
async def test_rewrite_validation() -> None:
    with pytest.raises(ValueError):
        await ai_assist.rewrite_text("  ")


@pytest.mark.asyncio
async def test_summarize_validation() -> None:
    with pytest.raises(ValueError):
        await ai_assist.summarize_text("")


@pytest.mark.asyncio
async def test_call_openai_remote(monkeypatch):
    class DummyResp:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict:
            return {"choices": [{"message": {"content": "Hi"}}]}

    class DummyClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        async def post(self, *args, **kwargs):
            return DummyResp()

    monkeypatch.setattr(ai_assist, "OPENAI_KEY", "k")
    monkeypatch.setattr(ai_assist.httpx, "AsyncClient", lambda timeout=10: DummyClient())

    result = await ai_assist._call_openai("ping")
    assert result == "Hi"


@pytest.mark.asyncio
async def test_call_openai_error(monkeypatch):
    class DummyClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        async def post(self, *args, **kwargs):
            raise ai_assist.httpx.HTTPError("fail")

    monkeypatch.setattr(ai_assist, "OPENAI_KEY", "k")
    monkeypatch.setattr(ai_assist.httpx, "AsyncClient", lambda timeout=10: DummyClient())

    with pytest.raises(RuntimeError):
        await ai_assist._call_openai("boom")

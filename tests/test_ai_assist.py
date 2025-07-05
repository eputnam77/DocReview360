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

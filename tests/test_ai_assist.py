from types import TracebackType
from typing import Any

import pytest
from fastapi.testclient import TestClient

from docreview360 import ai_assist
from docreview360.api import app


@pytest.mark.asyncio
async def test_ai_rewrite_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_call(text: str) -> str:
        return "rewritten"

    from docreview360 import api

    monkeypatch.setattr(api, "rewrite_text", fake_call)
    client = TestClient(app)
    resp = client.post("/ai/rewrite", json={"text": "hello"})
    assert resp.status_code == 200
    assert resp.json()["result"] == "rewritten"


@pytest.mark.asyncio
async def test_ai_summarize_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_sum(text: str) -> str:
        return "summary"

    from docreview360 import api

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
async def test_call_openai_remote(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyResp:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict[str, Any]:
            return {"choices": [{"message": {"content": "Hi"}}]}

    class DummyClient:
        async def __aenter__(self) -> "DummyClient":
            return self

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
        ) -> None:
            pass

        async def post(self, *args: Any, **kwargs: Any) -> DummyResp:
            return DummyResp()

    monkeypatch.setattr(ai_assist, "OPENAI_KEY", "k")
    monkeypatch.setattr(ai_assist.httpx, "AsyncClient", lambda timeout=10: DummyClient())

    result = await ai_assist._call_openai("ping")
    assert result == "Hi"


@pytest.mark.asyncio
async def test_call_openai_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyClient:
        async def __aenter__(self) -> "DummyClient":
            return self

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
        ) -> None:
            pass

        async def post(self, *args: Any, **kwargs: Any) -> None:
            raise ai_assist.httpx.HTTPError("fail")

    monkeypatch.setattr(ai_assist, "OPENAI_KEY", "k")
    monkeypatch.setattr(ai_assist.httpx, "AsyncClient", lambda timeout=10: DummyClient())

    with pytest.raises(RuntimeError):
        await ai_assist._call_openai("boom")

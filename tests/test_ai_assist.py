import sys
from datetime import timedelta
from types import TracebackType
from typing import Any

import pytest
from fastapi.testclient import TestClient

from docreview360 import ai_assist, ai_utils, auth
from docreview360.api import app


def _alice_headers() -> dict[str, str]:
    try:
        auth.USER_REPOSITORY.create_user(
            "alice", auth.DEMO_USER_DEFAULTS["alice"]["password"],
            otp_secret=auth.DEMO_USER_DEFAULTS["alice"].get("otp_secret"),
        )
    except Exception:
        pass
    token = auth.create_access_token({"sub": "alice"}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_ai_rewrite_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_call(text: str) -> str:
        return "rewritten"

    tools_mod = sys.modules["docreview360.api.tools_router"]
    monkeypatch.setattr(tools_mod, "rewrite_text", fake_call)
    client = TestClient(app)
    resp = client.post("/ai/rewrite", json={"text": "hello"}, headers=_alice_headers())
    assert resp.status_code == 200
    assert resp.json()["result"] == "rewritten"


@pytest.mark.asyncio
async def test_ai_summarize_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_sum(text: str) -> str:
        return "summary"

    tools_mod = sys.modules["docreview360.api.tools_router"]
    monkeypatch.setattr(tools_mod, "summarize_text", fake_sum)
    client = TestClient(app)
    resp = client.post("/ai/summarize", json={"text": "some text"}, headers=_alice_headers())
    assert resp.status_code == 200
    assert resp.json()["result"] == "summary"


@pytest.mark.asyncio
async def test_call_openai_fallback() -> None:
    result = await ai_assist._call_openai("hello world")
    assert result == "world hello"


@pytest.mark.asyncio
async def test_call_openai_empty() -> None:
    with pytest.raises(ValueError):
        await ai_assist._call_openai(" ")


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


@pytest.mark.asyncio
async def test_call_openai_with_synth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ai_utils, "synth_enabled", True)
    result = await ai_assist._call_openai("This is a test")
    assert result == "tst Ths"
    monkeypatch.setattr(ai_utils, "synth_enabled", False)


@pytest.mark.asyncio
async def test_rewrite_and_summarize(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake(prompt: str) -> str:
        return "ok"

    monkeypatch.setattr(ai_assist, "_call_openai", fake)
    assert await ai_assist.rewrite_text("text") == "ok"
    assert await ai_assist.summarize_text("text") == "ok"

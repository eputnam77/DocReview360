import httpx
import pytest

from docreview360.stubs.task135 import task135


@pytest.mark.asyncio
async def test_task135_completed(monkeypatch):
    async def fake_post(self, url, json=None, timeout=None):
        req = httpx.Request("POST", url)
        return httpx.Response(
            200,
            json={
                "suggest": {"simple": [{"options": [{"text": "foo", "_score": 1.0}]}]}
            },
            request=req,
        )

    monkeypatch.setattr("httpx.AsyncClient.post", fake_post)
    res = await task135("http://example.com")
    assert res == ["foo"]

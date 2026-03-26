import httpx
from docreview360 import http_client


def test_verify_true_uses_secure_context(monkeypatch):
    captured = {}

    def fake_get(url, **kwargs):
        captured["verify"] = kwargs.get("verify")
        return httpx.Response(200)

    monkeypatch.setattr(httpx, "get", fake_get)
    http_client.get("https://example.com", verify=True)

    assert captured["verify"] is http_client._tls_context

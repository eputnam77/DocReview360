import ssl
import httpx

from docreview360 import http_client


def test_get_ignores_insecure_verify(monkeypatch):
    """Passing ``verify=False`` should not disable TLS verification."""

    captured = {}

    def fake_get(url, **kwargs):
        captured["verify"] = kwargs.get("verify")
        return httpx.Response(200)

    monkeypatch.setattr(httpx, "get", fake_get)
    http_client.get("https://example.com", verify=False)

    assert captured["verify"] is http_client._tls_context


def test_client_uses_secure_context(monkeypatch):
    """The helper should always use the shared TLS context."""

    captured = {}

    class FakeClient:
        def __init__(self, **kwargs):
            captured["verify"] = kwargs.get("verify")

    monkeypatch.setattr(httpx, "Client", FakeClient)
    http_client.client(verify=False)

    assert captured["verify"] is http_client._tls_context


def test_custom_context_upgraded(monkeypatch):
    """Custom contexts with older TLS versions should be upgraded."""

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS)
    ctx.minimum_version = ssl.TLSVersion.TLSv1

    captured = {}

    def fake_get(url, **kwargs):
        captured["verify"] = kwargs.get("verify")
        return httpx.Response(200)

    monkeypatch.setattr(httpx, "get", fake_get)
    http_client.get("https://example.com", verify=ctx)

    assert captured["verify"] is ctx
    assert ctx.minimum_version is ssl.TLSVersion.TLSv1_2


def test_empty_string_verify(monkeypatch):
    """Falsey but non-boolean values like "" should still enable TLS checks."""

    captured = {}

    def fake_get(url, **kwargs):
        captured["verify"] = kwargs.get("verify")
        return httpx.Response(200)

    monkeypatch.setattr(httpx, "get", fake_get)
    http_client.get("https://example.com", verify="")

    assert captured["verify"] is http_client._tls_context


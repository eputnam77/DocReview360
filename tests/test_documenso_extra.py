import httpx
import pytest

from docreview360 import documenso


def test_documenso_error_handling() -> None:
    with pytest.raises(ValueError):
        documenso.request_signature("", "user")
    sig_id, url = documenso.request_signature("doc1", "user")
    assert url.endswith(sig_id)
    with pytest.raises(KeyError):
        documenso.signature_status("bad")
    documenso.complete_signature(sig_id)
    assert documenso.signature_status(sig_id) == "signed"


def test_documenso_remote(monkeypatch) -> None:
    def fake_post(url: str, json: dict | None = None, timeout: int | None = None) -> httpx.Response:
        req = httpx.Request("POST", url)
        if url.endswith("complete"):
            return httpx.Response(200, request=req)
        return httpx.Response(200, json={"id": "sig", "url": "http://remote/sig"}, request=req)

    def fake_get(url: str, timeout: int | None = None) -> httpx.Response:
        req = httpx.Request("GET", url)
        return httpx.Response(200, json={"status": "signed"}, request=req)

    monkeypatch.setenv("DOCUMENSO_URL", "http://remote")
    monkeypatch.setattr(documenso, "DOCUMENSO_URL", "http://remote")
    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(httpx, "get", fake_get)

    sig_id, url = documenso.request_signature("doc1", "bob")
    assert sig_id == "sig" and url == "http://remote/sig"
    assert documenso.signature_status(sig_id) == "signed"
    documenso.complete_signature(sig_id)

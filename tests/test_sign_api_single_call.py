import pytest
from docreview360 import documenso
from docreview360.api import app
from fastapi.testclient import TestClient


def test_sign_status_called_once(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    def fake_status(sig_id: str) -> str:
        nonlocal calls
        calls += 1
        raise KeyError("missing")

    monkeypatch.setattr(documenso, "signature_status", fake_status)
    monkeypatch.setattr("docreview360.api.signature_status", fake_status)
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/sign/missing")
    assert resp.status_code == 500
    assert calls == 1

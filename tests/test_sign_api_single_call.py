import sys
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from docreview360 import auth, documenso
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


def test_sign_status_called_once(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    def fake_status(sig_id: str) -> str:
        nonlocal calls
        calls += 1
        raise KeyError("missing")

    monkeypatch.setattr(documenso, "signature_status", fake_status)
    docs_mod = sys.modules["docreview360.api.documents_router"]
    monkeypatch.setattr(docs_mod, "signature_status", fake_status)
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/sign/missing", headers=_alice_headers())
    assert resp.status_code == 500
    assert calls == 1

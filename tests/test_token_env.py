import importlib
import sys
from pathlib import Path

import pytest
from jose import jwt


def test_env_secret_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCREVIEW360_SECRET_KEY", "custom")
    monkeypatch.setenv("DOCREVIEW360_ALGORITHM", "HS256")
    monkeypatch.setenv("DOCREVIEW360_ACCESS_EXPIRE_MINUTES", "60")
    monkeypatch.setenv("DOCREVIEW360_OIDC_SECRET_KEY", "oidc")
    monkeypatch.setenv("DOCREVIEW360_OIDC_ALGORITHM", "HS256")
    monkeypatch.setenv("DOCREVIEW360_OIDC_EXPIRE_MINUTES", "60")
    src_root = Path(__file__).resolve().parents[1] / "src"
    sys.path.insert(0, str(src_root))
    auth = importlib.import_module("docreview360.auth")
    sys.path.remove(str(src_root))
    token = auth.create_access_token({"sub": "bob"})
    payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
    assert payload["sub"] == "bob"

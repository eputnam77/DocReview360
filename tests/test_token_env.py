import importlib

from jose import jwt

import docreview360.auth as auth


def test_env_secret_key(monkeypatch) -> None:
    monkeypatch.setenv("DOCREVIEW360_SECRET_KEY", "custom")
    importlib.reload(auth)
    token = auth.create_access_token({"sub": "bob"})
    payload = jwt.decode(token, "custom", algorithms=[auth.ALGORITHM])
    assert payload["sub"] == "bob"

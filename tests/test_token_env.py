import importlib

import docuflow.auth as auth
from jose import jwt


def test_env_secret_key(monkeypatch) -> None:
    monkeypatch.setenv("DOCUFLOW_SECRET_KEY", "custom")
    importlib.reload(auth)
    token = auth.create_access_token({"sub": "bob"})
    payload = jwt.decode(token, "custom", algorithms=[auth.ALGORITHM])
    assert payload["sub"] == "bob"

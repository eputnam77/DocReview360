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
    monkeypatch.setenv("DOCREVIEW360_ENV", "dev")
    src_root = Path(__file__).resolve().parents[1] / "src"
    sys.path.insert(0, str(src_root))
    sys.modules.pop("docreview360.auth", None)
    auth = importlib.import_module("docreview360.auth")
    sys.path.remove(str(src_root))
    token = auth.create_access_token({"sub": "bob"})
    payload = jwt.decode(
        token,
        auth.SECRET_KEY,
        algorithms=[auth.ALGORITHM],
        audience=auth.TOKEN_AUDIENCE,
        issuer=auth.TOKEN_ISSUER,
    )
    assert payload["sub"] == "bob"


def test_defaults_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "DOCREVIEW360_SECRET_KEY",
        "DOCREVIEW360_ALGORITHM",
        "DOCREVIEW360_ACCESS_EXPIRE_MINUTES",
        "DOCREVIEW360_OIDC_SECRET_KEY",
        "DOCREVIEW360_OIDC_SECRET_KEY_PREVIOUS",
        "DOCREVIEW360_OIDC_ALGORITHM",
        "DOCREVIEW360_OIDC_EXPIRE_MINUTES",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DOCREVIEW360_ENV", "dev")

    module_name = "docreview360.auth"
    sys.modules.pop(module_name, None)

    src_root = Path(__file__).resolve().parents[1] / "src"
    sys.path.insert(0, str(src_root))
    with pytest.warns(RuntimeWarning):
        auth = importlib.import_module(module_name)
    sys.path.remove(str(src_root))

    assert isinstance(auth.SECRET_KEY, str)
    assert len(auth.SECRET_KEY) >= 32
    assert auth.ALGORITHM == "HS256"
    assert auth.ACCESS_TOKEN_EXPIRE_MINUTES == 30
    assert isinstance(auth.OIDC_SECRET_KEY, str)
    assert len(auth.OIDC_SECRET_KEY) >= 32
    assert auth.OIDC_ALGORITHM == "HS256"
    assert auth.OIDC_TOKEN_EXPIRE_MINUTES == 30

    token = auth.create_access_token({"sub": "alice"})
    payload = jwt.decode(
        token,
        auth.SECRET_KEY,
        algorithms=[auth.ALGORITHM],
        audience=auth.TOKEN_AUDIENCE,
        issuer=auth.TOKEN_ISSUER,
    )
    assert payload["sub"] == "alice"


def test_oidc_previous_secret_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCREVIEW360_SECRET_KEY", "custom")
    monkeypatch.setenv("DOCREVIEW360_OIDC_SECRET_KEY", "oidc-current")
    monkeypatch.setenv("DOCREVIEW360_OIDC_SECRET_KEY_PREVIOUS", "oidc-previous")
    monkeypatch.setenv("DOCREVIEW360_ENV", "dev")

    module_name = "docreview360.auth"
    sys.modules.pop(module_name, None)

    src_root = Path(__file__).resolve().parents[1] / "src"
    sys.path.insert(0, str(src_root))
    auth = importlib.import_module(module_name)
    sys.path.remove(str(src_root))

    assert auth.OIDC_SECRET_KEY_PREVIOUS == "oidc-previous"

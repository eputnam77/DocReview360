"""Tests for enforcing secret configuration based on DOCREVIEW360_ENV."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest


def _reload_auth() -> None:
    module_name = "docreview360.auth"
    sys.modules.pop(module_name, None)
    src_root = Path(__file__).resolve().parents[2] / "src"
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))


def test_missing_secret_in_production_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Importing auth should abort when secrets are missing in production."""

    for name in ("DOCREVIEW360_SECRET_KEY", "DOCREVIEW360_OIDC_SECRET_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DOCREVIEW360_ENV", "production")

    _reload_auth()

    with pytest.raises(RuntimeError) as excinfo:
        importlib.import_module("docreview360.auth")

    assert "DOCREVIEW360_SECRET_KEY" in str(excinfo.value)


def test_missing_secret_in_dev_warns(monkeypatch: pytest.MonkeyPatch) -> None:
    """Development builds fall back to defaults with a warning."""

    for name in (
        "DOCREVIEW360_SECRET_KEY",
        "DOCREVIEW360_OIDC_SECRET_KEY",
        "DOCREVIEW360_ALGORITHM",
        "DOCREVIEW360_ACCESS_EXPIRE_MINUTES",
        "DOCREVIEW360_OIDC_ALGORITHM",
        "DOCREVIEW360_OIDC_EXPIRE_MINUTES",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DOCREVIEW360_ENV", "dev")

    _reload_auth()

    with pytest.warns(RuntimeWarning):
        auth = importlib.import_module("docreview360.auth")

    assert auth.SECRET_KEY == "docreview360-dev-secret"
    assert auth.OIDC_SECRET_KEY == "docreview360-oidc-dev-secret"

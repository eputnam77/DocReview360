import os
import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DOCREVIEW360_SECRET_KEY", "test-secret")
os.environ.setdefault("DOCREVIEW360_ALGORITHM", "HS256")
os.environ.setdefault("DOCREVIEW360_ACCESS_EXPIRE_MINUTES", "30")
os.environ.setdefault("DOCREVIEW360_OIDC_SECRET_KEY", "test-oidc")
os.environ.setdefault("DOCREVIEW360_OIDC_ALGORITHM", "HS256")
os.environ.setdefault("DOCREVIEW360_OIDC_EXPIRE_MINUTES", "30")


@pytest.fixture(autouse=True)
def _set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure required auth environment variables are set for tests."""

    monkeypatch.setenv("DOCREVIEW360_SECRET_KEY", "test-secret")
    monkeypatch.setenv("DOCREVIEW360_ALGORITHM", "HS256")
    monkeypatch.setenv("DOCREVIEW360_ACCESS_EXPIRE_MINUTES", "30")
    monkeypatch.setenv("DOCREVIEW360_OIDC_SECRET_KEY", "test-oidc")
    monkeypatch.setenv("DOCREVIEW360_OIDC_ALGORITHM", "HS256")
    monkeypatch.setenv("DOCREVIEW360_OIDC_EXPIRE_MINUTES", "30")

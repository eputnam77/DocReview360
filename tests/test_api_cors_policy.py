import pytest
from docreview360.api import _LOCAL_CORS_ORIGINS, _resolve_cors_origins


def test_resolve_cors_origins_returns_local_defaults_for_dev() -> None:
    assert _resolve_cors_origins(None, environment="dev") == _LOCAL_CORS_ORIGINS


def test_resolve_cors_origins_requires_allowlist_for_production() -> None:
    with pytest.raises(RuntimeError, match="DOCREVIEW360_ALLOW_ORIGINS"):
        _resolve_cors_origins(None, environment="production")


def test_resolve_cors_origins_accepts_explicit_allowlist() -> None:
    origins = _resolve_cors_origins(
        "https://a.example, https://b.example",
        environment="production",
    )
    assert origins == ["https://a.example", "https://b.example"]

def test_resolve_cors_origins_rejects_prod_alias() -> None:
    with pytest.raises(RuntimeError, match="DOCREVIEW360_ENV must be set to 'production'"):
        _resolve_cors_origins(None, environment="prod")

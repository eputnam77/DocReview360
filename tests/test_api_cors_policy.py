import re

import pytest

from docreview360.api import (
    _LOCAL_CORS_ORIGIN_REGEX,
    _LOCAL_CORS_ORIGINS,
    _resolve_cors_origin_regex,
    _resolve_cors_origins,
)


def test_resolve_cors_origins_returns_local_defaults_for_dev() -> None:
    assert _resolve_cors_origins(None, environment="dev") == _LOCAL_CORS_ORIGINS


def test_resolve_cors_origin_regex_allows_same_host_dev_ports() -> None:
    pattern = _resolve_cors_origin_regex(None, environment="dev")

    assert pattern == _LOCAL_CORS_ORIGIN_REGEX
    assert re.match(pattern, "http://workstation:3000")
    assert re.match(pattern, "https://preview-host:8000")
    assert not re.match(pattern, "https://app.example.com:443")


def test_resolve_cors_origins_requires_allowlist_for_production() -> None:
    with pytest.raises(RuntimeError, match="DOCREVIEW360_ALLOW_ORIGINS"):
        _resolve_cors_origins(None, environment="production")


def test_resolve_cors_origin_regex_is_disabled_when_allowlist_is_explicit() -> None:
    assert _resolve_cors_origin_regex("https://app.example.com", environment="production") is None


def test_resolve_cors_origins_accepts_explicit_allowlist() -> None:
    origins = _resolve_cors_origins(
        "https://a.example, https://b.example",
        environment="production",
    )
    assert origins == ["https://a.example", "https://b.example"]


def test_resolve_cors_origins_rejects_wildcard_in_production() -> None:
    with pytest.raises(RuntimeError, match="must not include '\\*'"):
        _resolve_cors_origins("*", environment="production")


def test_resolve_cors_origins_rejects_prod_alias() -> None:
    with pytest.raises(RuntimeError, match="DOCREVIEW360_ENV must be set to 'production'"):
        _resolve_cors_origins(None, environment="prod")


def test_resolve_cors_origin_regex_rejects_prod_alias() -> None:
    with pytest.raises(RuntimeError, match="DOCREVIEW360_ENV must be set to 'production'"):
        _resolve_cors_origin_regex(None, environment="prod")

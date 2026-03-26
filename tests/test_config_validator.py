# SPDX-License-Identifier: MIT
"""Tests for docreview360.config_validator — startup configuration validation."""

from __future__ import annotations

import pytest
from docreview360.config_validator import (
    ConfigValidationError,
    _check_cors_origins,
    _check_debug_off_in_production,
    _check_secret_key,
    validate_startup_config,
)

# ---------------------------------------------------------------------------
# _check_secret_key
# ---------------------------------------------------------------------------


def test_secret_key_skipped_in_dev_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCREVIEW360_ENV", "dev")
    monkeypatch.delenv("DOCREVIEW360_SECRET_KEY", raising=False)
    errors: list[str] = []
    _check_secret_key(errors)
    assert errors == []


def test_secret_key_required_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCREVIEW360_ENV", "production")
    monkeypatch.delenv("DOCREVIEW360_SECRET_KEY", raising=False)
    errors: list[str] = []
    _check_secret_key(errors)
    assert any("not set" in e for e in errors)


def test_secret_key_too_short_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCREVIEW360_ENV", "production")
    monkeypatch.setenv("DOCREVIEW360_SECRET_KEY", "short")
    errors: list[str] = []
    _check_secret_key(errors)
    assert any("too short" in e for e in errors)


def test_secret_key_placeholder_rejected_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCREVIEW360_ENV", "production")
    monkeypatch.setenv("DOCREVIEW360_SECRET_KEY", "changeme")
    errors: list[str] = []
    _check_secret_key(errors)
    assert any("insecure placeholder" in e for e in errors)


def test_strong_secret_key_accepted_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCREVIEW360_ENV", "production")
    monkeypatch.setenv("DOCREVIEW360_SECRET_KEY", "a" * 40)
    errors: list[str] = []
    _check_secret_key(errors)
    assert errors == []


# ---------------------------------------------------------------------------
# _check_debug_off_in_production
# ---------------------------------------------------------------------------


def test_debug_allowed_in_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCREVIEW360_ENV", "dev")
    monkeypatch.setenv("DOCREVIEW360_DEBUG", "true")
    errors: list[str] = []
    _check_debug_off_in_production(errors)
    assert errors == []


def test_debug_true_rejected_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCREVIEW360_ENV", "production")
    monkeypatch.setenv("DOCREVIEW360_DEBUG", "1")
    errors: list[str] = []
    _check_debug_off_in_production(errors)
    assert any("DOCREVIEW360_DEBUG" in e for e in errors)


def test_debug_off_ok_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCREVIEW360_ENV", "production")
    monkeypatch.setenv("DOCREVIEW360_DEBUG", "0")
    errors: list[str] = []
    _check_debug_off_in_production(errors)
    assert errors == []


# ---------------------------------------------------------------------------
# _check_cors_origins
# ---------------------------------------------------------------------------


def test_wildcard_cors_rejected_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCREVIEW360_ENV", "production")
    monkeypatch.setenv("DOCREVIEW360_CORS_ORIGINS", "*")
    errors: list[str] = []
    _check_cors_origins(errors)
    assert any("CORS" in e for e in errors)


def test_wildcard_cors_allowed_in_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCREVIEW360_ENV", "dev")
    monkeypatch.setenv("DOCREVIEW360_CORS_ORIGINS", "*")
    errors: list[str] = []
    _check_cors_origins(errors)
    assert errors == []


def test_explicit_cors_ok_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCREVIEW360_ENV", "production")
    monkeypatch.setenv("DOCREVIEW360_CORS_ORIGINS", "https://app.example.com")
    errors: list[str] = []
    _check_cors_origins(errors)
    assert errors == []


# ---------------------------------------------------------------------------
# validate_startup_config (integration)
# ---------------------------------------------------------------------------


def test_validate_startup_passes_in_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCREVIEW360_ENV", "dev")
    # Should not raise in dev environment
    validate_startup_config()


def test_validate_startup_raises_on_multiple_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCREVIEW360_ENV", "production")
    monkeypatch.delenv("DOCREVIEW360_SECRET_KEY", raising=False)
    monkeypatch.setenv("DOCREVIEW360_DEBUG", "true")
    monkeypatch.setenv("DOCREVIEW360_CORS_ORIGINS", "*")

    with pytest.raises(ConfigValidationError) as exc_info:
        validate_startup_config()

    err = exc_info.value
    assert len(err.errors) >= 3
    combined = str(err)
    assert "Configuration validation failed" in combined


def test_config_validation_error_message_format() -> None:
    err = ConfigValidationError(["error one", "error two"])
    msg = str(err)
    assert "error one" in msg
    assert "error two" in msg

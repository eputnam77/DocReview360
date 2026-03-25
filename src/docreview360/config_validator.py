# SPDX-License-Identifier: MIT
"""Startup configuration validation for DocReview360.

This module performs security-focused and environment-specific checks
*before* the application begins accepting requests.  It supplements
the field-level validation already present on :class:`~docreview360.config.Config`.

Usage::

    from docreview360.config_validator import validate_startup_config

    # raises ConfigValidationError on any failure
    validate_startup_config()
"""

from __future__ import annotations

import logging
import os

_logger = logging.getLogger(__name__)

# Minimum acceptable secret-key length (characters).
_MIN_SECRET_KEY_LEN = 32

# Known insecure placeholder values that must not be used in production.
_INSECURE_PLACEHOLDERS = {
    "secret",
    "changeme",
    "your-secret-key",
    "test-secret",
    "development",
    "insecure",
    "password",
}


class ConfigValidationError(Exception):
    """Raised when startup configuration is invalid."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        bullet_list = "\n".join(f"  • {e}" for e in errors)
        super().__init__(f"Configuration validation failed:\n{bullet_list}")


def _check_secret_key(errors: list[str]) -> None:
    """Validate DOCREVIEW360_SECRET_KEY strength."""
    env = os.getenv("DOCREVIEW360_ENV", "prod").lower()
    if env in ("dev", "development", "test"):
        return  # relaxed rules in non-production

    key = os.getenv("DOCREVIEW360_SECRET_KEY", "")
    if not key:
        errors.append("DOCREVIEW360_SECRET_KEY is not set")
        return
    if len(key) < _MIN_SECRET_KEY_LEN:
        errors.append(
            f"DOCREVIEW360_SECRET_KEY is too short ({len(key)} chars); "
            f"minimum is {_MIN_SECRET_KEY_LEN}"
        )
    if key.lower().strip() in _INSECURE_PLACEHOLDERS:
        errors.append(
            "DOCREVIEW360_SECRET_KEY is a known insecure placeholder value"
        )


def _check_debug_off_in_production(errors: list[str]) -> None:
    """Ensure debug mode is not enabled in production."""
    env = os.getenv("DOCREVIEW360_ENV", "prod").lower()
    if env in ("dev", "development", "test"):
        return
    debug_val = os.getenv("DOCREVIEW360_DEBUG", "0").lower()
    if debug_val in ("1", "true", "yes"):
        errors.append(
            "DOCREVIEW360_DEBUG=true must not be set in production environments"
        )


def _check_cors_origins(errors: list[str]) -> None:
    """Warn when CORS origins are set to the wildcard '*' in production."""
    env = os.getenv("DOCREVIEW360_ENV", "prod").lower()
    if env in ("dev", "development", "test"):
        return
    origins = os.getenv("DOCREVIEW360_CORS_ORIGINS", "")
    if origins.strip() == "*":
        errors.append(
            "DOCREVIEW360_CORS_ORIGINS='*' is not safe for production; "
            "specify explicit allowed origins"
        )


def _check_database_url(errors: list[str]) -> None:
    """Ensure DATABASE_URL is set when not using the default SQLite fallback."""
    env = os.getenv("DOCREVIEW360_ENV", "prod").lower()
    if env in ("dev", "development", "test"):
        return
    db_url = os.getenv("DOCREVIEW360_DATABASE_URL", "")
    if not db_url:
        _logger.warning(
            "DOCREVIEW360_DATABASE_URL is not set; "
            "the application will use the SQLite fallback which is not "
            "recommended for production deployments"
        )


def validate_startup_config() -> None:
    """Run all startup configuration checks.

    Collects all failures and raises :class:`ConfigValidationError` once so
    operators can fix everything in a single pass.

    Also performs non-fatal checks that emit log warnings rather than errors.

    Raises:
        ConfigValidationError: if any mandatory check fails.
    """
    errors: list[str] = []

    _check_secret_key(errors)
    _check_debug_off_in_production(errors)
    _check_cors_origins(errors)
    _check_database_url(errors)  # warning-only

    if errors:
        raise ConfigValidationError(errors)

    _logger.info("Startup configuration validation passed")

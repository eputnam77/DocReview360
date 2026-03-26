# SPDX-License-Identifier: MIT
"""Tests that settings.yaml is present and contains the expected top-level keys.

These tests act as a lightweight guard: they do not validate every value but
ensure that keys required for production operation have not been accidentally
removed from the file.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SETTINGS_FILE = REPO_ROOT / "settings.yaml"


@pytest.fixture(scope="module")
def settings() -> dict:  # type: ignore[type-arg]
    """Load settings.yaml once for the module."""
    with SETTINGS_FILE.open() as fh:
        data = yaml.safe_load(fh)
    return data or {}


def test_settings_file_exists() -> None:
    """settings.yaml must exist at the repository root."""
    assert SETTINGS_FILE.exists(), f"Missing settings.yaml at {SETTINGS_FILE}"


def test_required_top_level_keys(settings: dict) -> None:  # type: ignore[type-arg]
    """Key sections required for production must be present."""
    required = [
        "audit_log",
        "security",
        "signature_provider_primary",
        "signature_verification",
        "notifications",
    ]
    missing = [k for k in required if k not in settings]
    assert not missing, f"Missing required keys in settings.yaml: {missing}"


def test_audit_log_retention(settings: dict) -> None:  # type: ignore[type-arg]
    """audit_log section must define retention_days and purge_interval_minutes."""
    al = settings.get("audit_log", {})
    assert "retention_days" in al, "audit_log.retention_days is missing"
    assert "purge_interval_minutes" in al, "audit_log.purge_interval_minutes is missing"
    assert int(al["retention_days"]) > 0, "audit_log.retention_days must be positive"


def test_encryption_at_rest_enabled(settings: dict) -> None:  # type: ignore[type-arg]
    """Encryption at rest must be enabled (security.encryption_at_rest.enabled)."""
    eat = settings.get("security", {}).get("encryption_at_rest", {})
    assert eat.get("enabled") is True, (
        "security.encryption_at_rest.enabled must be true; "
        "disabling it exposes archive/backup data."
    )


def test_signature_provider_is_present(settings: dict) -> None:  # type: ignore[type-arg]
    """signature_provider_primary must be defined (warn if sandbox)."""
    provider = settings.get("signature_provider_primary")
    assert provider is not None, "signature_provider_primary is missing from settings.yaml"
    # Not an error in test environments, but emit a note so reviewers notice.
    if provider == "sandbox":
        pytest.skip(
            "signature_provider_primary=sandbox is acceptable in dev/test but "
            "must be overridden in production (e.g. set SIGNATURE_PROVIDER=documenso)."
        )


def test_no_plaintext_slack_test_webhook(settings: dict) -> None:  # type: ignore[type-arg]
    """The known test Slack webhook URL must not be present in a production file.

    This test is skipped in non-production environments (DOCREVIEW360_ENV != production).
    """
    import os

    if os.environ.get("DOCREVIEW360_ENV", "dev") != "production":
        pytest.skip("Webhook check only enforced when DOCREVIEW360_ENV=production")

    webhook = settings.get("notifications", {}).get("slack_webhook_url", "")
    assert "test123" not in webhook, (
        "settings.yaml contains the placeholder Slack webhook URL "
        "(https://hooks.slack.com/test123). Replace it before deploying to production."
    )

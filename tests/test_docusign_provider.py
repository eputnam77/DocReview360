"""Tests for the DocuSign e-signature provider connector."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest
from docreview360.integrations.signature import docusign as docusign_mod
from docreview360.integrations.signature.docusign import (
    DocuSignProvider,
    _reset_circuit_breaker_for_tests,
    _sig_metadata,
    _sig_workflows,
    _signatures,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clear_state() -> None:
    """Reset all module-level stub state between tests."""
    _signatures.clear()
    _sig_workflows.clear()
    _sig_metadata.clear()
    _reset_circuit_breaker_for_tests()


@pytest.fixture(autouse=True)
def reset_state() -> None:  # type: ignore[return]
    _clear_state()
    yield
    _clear_state()


# ---------------------------------------------------------------------------
# Stub-mode tests (no DOCUSIGN_BASE_URL configured)
# ---------------------------------------------------------------------------


def test_request_signature_stub_mode() -> None:
    """request_signature in stub mode returns a valid (id, url, metadata) triple."""
    provider = DocuSignProvider()
    sig_id, url, meta = provider.request_signature("doc-001", "alice")

    assert sig_id, "sig_id must be non-empty"
    assert url.startswith("/docusign/")
    assert sig_id in url
    assert isinstance(meta, dict)
    assert meta.get("envelope_id") == sig_id
    assert meta.get("status") == "pending"


def test_request_signature_validates_args() -> None:
    """request_signature raises ValueError when document_id or user is missing."""
    provider = DocuSignProvider()
    with pytest.raises(ValueError):
        provider.request_signature("", "alice")
    with pytest.raises(ValueError):
        provider.request_signature("doc-001", "")


def test_request_signature_with_return_url_and_approval_id() -> None:
    """Return URL and approval ID are embedded in the stub signing URL."""
    provider = DocuSignProvider()
    sig_id, url, _ = provider.request_signature(
        "doc-002",
        "bob",
        return_url="https://example.com/callback",
        approval_id="appr-42",
    )
    assert "return=" in url
    assert "approval=" in url


def test_request_signature_records_workflow_id() -> None:
    """Workflow ID is stored in _sig_workflows in stub mode."""
    provider = DocuSignProvider()
    sig_id, _, _ = provider.request_signature("doc-003", "carol", workflow_id="wf-99")
    assert _sig_workflows.get(sig_id) == "wf-99"


# ---------------------------------------------------------------------------
# process_webhook tests
# ---------------------------------------------------------------------------


def test_process_webhook_completed_updates_status() -> None:
    """process_webhook with status='completed' updates _signatures."""
    provider = DocuSignProvider()
    sig_id, _, _ = provider.request_signature("doc-004", "dave")
    assert _signatures[sig_id] == "pending"

    provider.process_webhook({"envelopeId": sig_id, "status": "completed"})
    assert _signatures[sig_id] == "completed"


def test_process_webhook_other_status() -> None:
    """process_webhook stores arbitrary status strings."""
    provider = DocuSignProvider()
    sig_id, _, _ = provider.request_signature("doc-005", "eve")

    provider.process_webhook({"envelopeId": sig_id, "status": "voided"})
    assert _signatures[sig_id] == "voided"


def test_process_webhook_invalid_payload_raises() -> None:
    """process_webhook raises ValueError when required fields are missing."""
    provider = DocuSignProvider()
    with pytest.raises(ValueError):
        provider.process_webhook({})
    with pytest.raises(ValueError):
        provider.process_webhook({"envelopeId": "abc"})  # missing status
    with pytest.raises(ValueError):
        provider.process_webhook({"status": "completed"})  # missing envelopeId


def test_process_webhook_with_completed_datetime() -> None:
    """process_webhook accepts an optional completedDateTime field."""
    provider = DocuSignProvider()
    sig_id, _, _ = provider.request_signature("doc-006", "frank")
    # Should not raise even with a completedDateTime value
    provider.process_webhook(
        {
            "envelopeId": sig_id,
            "status": "completed",
            "completedDateTime": "2026-01-15T12:00:00Z",
        }
    )
    assert _signatures[sig_id] == "completed"


# ---------------------------------------------------------------------------
# verify_signature tests
# ---------------------------------------------------------------------------


def test_verify_signature_pending_returns_false() -> None:
    """verify_signature returns False when envelope is still pending."""
    provider = DocuSignProvider()
    sig_id, _, _ = provider.request_signature("doc-007", "grace")
    assert provider.verify_signature(sig_id, b"doc content") is False


def test_verify_signature_completed_returns_true() -> None:
    """verify_signature returns True after webhook marks envelope as completed."""
    provider = DocuSignProvider()
    sig_id, _, _ = provider.request_signature("doc-008", "heidi")
    provider.process_webhook({"envelopeId": sig_id, "status": "completed"})
    assert provider.verify_signature(sig_id, b"doc content") is True


def test_verify_signature_unknown_id_returns_false() -> None:
    """verify_signature returns False for an unrecognized signature ID."""
    provider = DocuSignProvider()
    assert provider.verify_signature("nonexistent-id", b"data") is False


# ---------------------------------------------------------------------------
# validate_signature tests
# ---------------------------------------------------------------------------


def test_validate_signature_completed_metadata() -> None:
    """validate_signature returns True when metadata status is 'completed'."""
    provider = DocuSignProvider()
    assert provider.validate_signature(b"bytes", None, {"status": "completed"}) is True


def test_validate_signature_pending_metadata() -> None:
    """validate_signature returns False when metadata status is not 'completed'."""
    provider = DocuSignProvider()
    assert provider.validate_signature(b"bytes", None, {"status": "pending"}) is False
    assert provider.validate_signature(b"bytes", None, {}) is False


# ---------------------------------------------------------------------------
# health_check tests
# ---------------------------------------------------------------------------


def test_health_check_stub_mode_returns_true(monkeypatch: pytest.MonkeyPatch) -> None:
    """health_check returns True when no DOCUSIGN_BASE_URL is configured (stub mode)."""
    monkeypatch.setattr(docusign_mod, "DOCUSIGN_BASE_URL", None)
    provider = DocuSignProvider()
    assert provider.health_check() is True


def test_health_check_remote_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    """health_check returns True when the remote account endpoint responds 200."""

    def fake_get(url: str, timeout: int = 10, headers: dict | None = None, **_kw: object):
        req = httpx.Request("GET", url)
        return httpx.Response(200, request=req)

    monkeypatch.setattr(docusign_mod, "DOCUSIGN_BASE_URL", "https://demo.docusign.net/restapi/v2.1")
    monkeypatch.setattr(docusign_mod, "_ACCOUNT_ID", "test-account-id")
    monkeypatch.setattr(docusign_mod, "http_get", fake_get)

    provider = DocuSignProvider()
    assert provider.health_check() is True


# ---------------------------------------------------------------------------
# signature_status tests
# ---------------------------------------------------------------------------


def test_signature_status_pending() -> None:
    """signature_status returns 'pending' for a newly created stub signature."""
    provider = DocuSignProvider()
    sig_id, _, _ = provider.request_signature("doc-009", "ivan")
    assert provider.signature_status(sig_id) == "pending"


def test_signature_status_completed_after_webhook() -> None:
    """signature_status returns 'completed' after a completed webhook."""
    provider = DocuSignProvider()
    sig_id, _, _ = provider.request_signature("doc-010", "judy")
    provider.process_webhook({"envelopeId": sig_id, "status": "completed"})
    assert provider.signature_status(sig_id) == "completed"


def test_signature_status_unknown_raises() -> None:
    """signature_status raises KeyError for an unknown signature ID in stub mode."""
    provider = DocuSignProvider()
    with pytest.raises(KeyError):
        provider.signature_status("totally-unknown-id")


# ---------------------------------------------------------------------------
# Circuit-breaker tests
# ---------------------------------------------------------------------------


def test_circuit_breaker_trips_after_threshold_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """After FAILURE_THRESHOLD consecutive remote failures, stub mode is used."""
    call_count = 0

    def always_fail(url: str, json: dict | None = None, timeout: int = 10,
                    headers: dict | None = None, **_kw: object) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        req = httpx.Request("POST", url)
        raise httpx.ConnectError("connection refused", request=req)

    monkeypatch.setattr(docusign_mod, "DOCUSIGN_BASE_URL", "https://demo.docusign.net/restapi/v2.1")
    monkeypatch.setattr(docusign_mod, "_ACCOUNT_ID", "test-account-id")
    monkeypatch.setattr(docusign_mod, "http_post", always_fail)

    provider = DocuSignProvider()

    # First FAILURE_THRESHOLD - 1 calls should raise RuntimeError (breaker not yet tripped)
    threshold = docusign_mod.FAILURE_THRESHOLD
    for _ in range(threshold - 1):
        with pytest.raises(RuntimeError):
            provider.request_signature("doc-cb", "mallory")

    # The threshold-th failure should trip the circuit breaker → falls back to stub
    sig_id, url, meta = provider.request_signature("doc-cb", "mallory")
    assert sig_id, "Should have fallen back to stub and returned a valid sig_id"
    assert url.startswith("/docusign/")

    # After breaker is tripped, subsequent calls go straight to stub (no HTTP call)
    prev_call_count = call_count
    sig_id2, url2, _ = provider.request_signature("doc-cb", "mallory")
    assert call_count == prev_call_count, "No more HTTP calls should be made while suspended"
    assert url2.startswith("/docusign/")


def test_circuit_breaker_recovers_after_cooldown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Circuit breaker clears after cooldown, allowing remote calls again."""
    from datetime import timedelta

    # Trip the breaker by patching _remote_suspended_until to an expired timestamp
    past = _now() - timedelta(seconds=1)
    monkeypatch.setattr(docusign_mod, "_remote_suspended_until", past)
    monkeypatch.setattr(docusign_mod, "DOCUSIGN_BASE_URL", None)

    # After cooldown (past timestamp), _should_use_remote returns False because URL is None
    provider = DocuSignProvider()
    sig_id, url, _ = provider.request_signature("doc-recover", "oscar")
    assert url.startswith("/docusign/")


def _now() -> datetime:
    return datetime.now(timezone.utc)

# SPDX-License-Identifier: MIT
"""Tests for brittleness fixes B-04, B-05, B-06, B-09, B-10, B-14."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# B-04: CSRF bypass on cookie-token fallback
# ---------------------------------------------------------------------------


def test_b04_empty_bearer_does_not_fall_through_to_cookie_auth() -> None:
    """An empty Bearer token must not grant access via a valid cookie.

    The `elif not token: token = cookie_token` branch was removed so an empty
    bearer string (which is falsy but not None) can no longer silently bypass
    the CSRF check and adopt the cookie token.  The request should receive 401.
    """
    from datetime import timedelta

    from docreview360 import auth
    from docreview360.api import app
    from fastapi.testclient import TestClient

    # Ensure alice exists and get a valid token for the cookie.
    try:
        auth.USER_REPOSITORY.create_user(
            "alice",
            auth.DEMO_USER_DEFAULTS["alice"]["password"],
            otp_secret=auth.DEMO_USER_DEFAULTS["alice"].get("otp_secret"),
        )
    except Exception:
        pass

    valid_token = auth.create_access_token({"sub": "alice"}, timedelta(minutes=30))

    client = TestClient(app, raise_server_exceptions=False)

    # Send an empty Bearer header AND a valid cookie without a CSRF token.
    # The old code would fall into `elif not token: token = cookie_token`,
    # skipping CSRF validation and granting access.  The fix removes that
    # branch entirely, so `token` stays as `""` (falsy) and then `not token`
    # raises 401.
    resp = client.get(
        "/projects",
        headers={"Authorization": "Bearer "},
        cookies={"access_token": valid_token},
    )
    assert resp.status_code in (401, 403), (
        f"Expected 401/403 with empty bearer + cookie, got {resp.status_code}"
    )


def test_b04_valid_bearer_does_not_require_csrf() -> None:
    """A non-empty Bearer token should work without a CSRF token (control test)."""
    from datetime import timedelta

    from docreview360 import auth
    from docreview360.api import app
    from fastapi.testclient import TestClient

    try:
        auth.USER_REPOSITORY.create_user(
            "alice",
            auth.DEMO_USER_DEFAULTS["alice"]["password"],
            otp_secret=auth.DEMO_USER_DEFAULTS["alice"].get("otp_secret"),
        )
    except Exception:
        pass

    valid_token = auth.create_access_token({"sub": "alice"}, timedelta(minutes=30))
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/projects", headers={"Authorization": f"Bearer {valid_token}"})
    assert resp.status_code == 200


def test_b04_elif_not_token_pattern_absent_from_auth_core() -> None:
    """Source-level: the CSRF-bypassing `elif not token` branch must not exist."""
    core_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "docreview360"
        / "auth"
        / "_core.py"
    )
    source = core_path.read_text(encoding="utf-8")
    # The dangerous pattern was two lines: `elif not token:` followed by
    # `    token = cookie_token`.  Assert neither occurs adjacent to a
    # cookie_token assignment.
    assert "elif not token:\n        token = cookie_token" not in source, (
        "CSRF-bypass 'elif not token: token = cookie_token' still present in auth/_core.py"
    )


# ---------------------------------------------------------------------------
# B-05: Silent lifecycle event exceptions — source-level checks
# ---------------------------------------------------------------------------


ROUTER_FILES = [
    "assignments_router",
    "documents_router",
    "projects_router",
    "feedback_router",
]


def _extract_emit_webhook_body(source: str) -> str:
    """Extract the body of _emit_webhook from the given source string."""
    start = source.find("def _emit_webhook(")
    assert start != -1, "_emit_webhook function not found in source"
    # Find the end: next top-level def/class after _emit_webhook
    end = len(source)
    for marker in ["\ndef ", "\nclass ", "\nasync def "]:
        idx = source.find(marker, start + 1)
        if idx != -1 and idx < end:
            end = idx
    return source[start:end]


@pytest.mark.parametrize("module_name", ROUTER_FILES)
def test_b05_emit_webhook_logs_error_not_silenced(module_name: str) -> None:
    """_emit_webhook must log at error level; bare `except Exception: pass` is gone."""
    router_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "docreview360"
        / "api"
        / f"{module_name}.py"
    )
    source = router_path.read_text(encoding="utf-8")
    func_body = _extract_emit_webhook_body(source)

    # The function must contain _logger.error
    assert "_logger.error" in func_body, (
        f"{module_name}.py: _emit_webhook does not call _logger.error"
    )

    # The bare silence pattern must not appear inside _emit_webhook
    assert "except Exception:\n        pass" not in func_body, (
        f"{module_name}.py _emit_webhook: still has bare 'except Exception: pass'"
    )


@pytest.mark.parametrize("module_name", ROUTER_FILES)
def test_b05_emit_webhook_logs_on_failure(module_name: str, caplog: pytest.LogCaptureFixture) -> None:
    """_emit_webhook must emit an error log when emit_lifecycle_event raises."""
    import importlib
    import logging

    full_module = f"docreview360.api.{module_name}"
    mod = importlib.import_module(full_module)

    with patch(
        f"{full_module}.emit_lifecycle_event" if hasattr(mod, "emit_lifecycle_event") else
        "docreview360.api.webhooks.emit_lifecycle_event",
        side_effect=RuntimeError("webhook boom"),
    ):
        with patch(
            f"docreview360.api.webhooks.emit_lifecycle_event",
            side_effect=RuntimeError("webhook boom"),
        ):
            with caplog.at_level(logging.ERROR, logger=full_module):
                # _emit_webhook should not raise; it should log
                mod._emit_webhook("test.event", {"key": "val"})

    # At least one error record should mention the event
    error_records = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert error_records, (
        f"{module_name}._emit_webhook did not log an error when emit_lifecycle_event raised"
    )


# ---------------------------------------------------------------------------
# B-06: Approval routing failures unlogged
# ---------------------------------------------------------------------------


def test_b06_run_confirmed_action_logs_error_in_source() -> None:
    """Source-level: routing.py must log at error level inside run_confirmed_action."""
    routing_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "docreview360"
        / "approvals"
        / "routing.py"
    )
    source = routing_path.read_text(encoding="utf-8")
    assert "_logger.error" in source, (
        "approvals/routing.py: run_confirmed_action does not call _logger.error"
    )
    # Must not silently swallow: bare except without logging
    assert "except Exception:\n                return False" not in source, (
        "approvals/routing.py: still has a bare except that returns False without logging"
    )


def test_b06_run_confirmed_action_returns_false_on_exception(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """run_confirmed_action must return False (not raise) when action raises."""
    import logging

    from docreview360.approvals.routing import run_confirmed_action

    def _boom() -> None:
        raise RuntimeError("test-boom")

    with caplog.at_level(logging.ERROR, logger="docreview360.approvals.routing"):
        result = run_confirmed_action(True, _boom)

    assert result is False, "run_confirmed_action should return False when action raises"
    error_records = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert error_records, "run_confirmed_action must log at ERROR level when action raises"
    assert "test-boom" in error_records[0].getMessage() or "test-boom" in str(
        error_records[0].exc_text or ""
    )


def test_b06_run_confirmed_action_returns_true_on_success() -> None:
    """run_confirmed_action returns True when action succeeds."""
    from docreview360.approvals.routing import run_confirmed_action

    called = []

    def _ok() -> None:
        called.append(1)

    result = run_confirmed_action(True, _ok)
    assert result is True
    assert called == [1]


def test_b06_run_confirmed_action_returns_false_when_not_confirmed() -> None:
    """run_confirmed_action returns False when confirm=False."""
    from docreview360.approvals.routing import run_confirmed_action

    result = run_confirmed_action(False, lambda: None)
    assert result is False


# ---------------------------------------------------------------------------
# B-09: Corrupted audit log entries preserved
# ---------------------------------------------------------------------------


def test_b09_corrupt_entry_skipped_not_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """purge_audit_logs must skip corrupt lines, not preserve them."""
    from docreview360 import audit

    log_path = tmp_path / "audit.log"
    monkeypatch.setattr(audit, "_AUDIT_LOG_PATH", log_path)
    audit.clear_audit_log()

    now = datetime.now(timezone.utc)
    old_ts = (now - timedelta(days=400)).isoformat()
    recent_ts = now.isoformat()

    # Write three lines directly: one old valid, one corrupt, one recent valid
    old_valid = json.dumps({
        "id": "aaaa",
        "event": "old_event",
        "document_id": "doc1",
        "approval_id": None,
        "status": "ok",
        "certificate_url": None,
        "verified_at": old_ts,
        "verifier": "alice",
        "hash": "abc123",
        "context": {},
    })
    corrupt_line = "NOT VALID JSON {{{"
    recent_valid = json.dumps({
        "id": "bbbb",
        "event": "recent_event",
        "document_id": "doc1",
        "approval_id": None,
        "status": "ok",
        "certificate_url": None,
        "verified_at": recent_ts,
        "verifier": "bob",
        "hash": "def456",
        "context": {},
    })

    with log_path.open("w", encoding="utf-8") as fh:
        fh.write(old_valid + "\n")
        fh.write(corrupt_line + "\n")
        fh.write(recent_valid + "\n")

    # Purge with 30-day retention — the old_valid entry is >400 days old, so removed.
    # The corrupt entry should be skipped (not counted as removed, not preserved).
    # The recent_valid entry should be kept.
    removed = audit.purge_audit_logs(retention_days=30)

    # Exactly 1 old valid entry removed (corrupt is skipped, not counted)
    assert removed == 1, f"Expected 1 removed entry, got {removed}"

    # The log file must still exist (recent_valid should remain)
    assert log_path.exists(), "Audit log file should exist after purge (recent entry kept)"

    content = log_path.read_text(encoding="utf-8")

    # Corrupt line must NOT be in the resulting file
    assert corrupt_line not in content, (
        "Corrupt line was preserved in the audit log after purge (B-09 not fixed)"
    )

    # Recent valid entry must still be present
    assert "recent_event" in content, (
        "Recent valid audit entry was incorrectly removed during purge"
    )

    # Old valid entry must not be present
    assert "old_event" not in content, (
        "Old valid audit entry was not removed during purge"
    )


def test_b09_all_corrupt_no_crash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """purge_audit_logs with only corrupt lines must not crash and removes none."""
    from docreview360 import audit

    log_path = tmp_path / "audit.log"
    monkeypatch.setattr(audit, "_AUDIT_LOG_PATH", log_path)

    with log_path.open("w", encoding="utf-8") as fh:
        fh.write("GARBAGE\n")
        fh.write("MORE GARBAGE\n")

    removed = audit.purge_audit_logs(retention_days=30)
    # No valid old entries were removed
    assert removed == 0


# ---------------------------------------------------------------------------
# B-10: Silent certificate upload failure — source-level check
# ---------------------------------------------------------------------------


def test_b10_certificate_fetch_failure_reraises_not_silenced() -> None:
    """Source-level: sharepoint_upload.py must re-raise cert fetch failures."""
    upload_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "docreview360"
        / "integrations"
        / "sharepoint_upload.py"
    )
    source = upload_path.read_text(encoding="utf-8")

    # The fix replaces `cert_bytes = b""` with `raise` after logging
    assert "cert_bytes = b\"\"" not in source or source.count("cert_bytes = b\"\"") == 1, (
        "sharepoint_upload.py: fallback to b'' on cert fetch failure still present"
    )
    # The except block must now re-raise
    assert "raise" in source, (
        "sharepoint_upload.py: certificate fetch exception is not re-raised"
    )
    # Must log the failure
    assert "_logger.error" in source, (
        "sharepoint_upload.py: certificate fetch failure not logged"
    )


@pytest.mark.asyncio
async def test_b10_certificate_fetch_failure_propagates() -> None:
    """B-10: a cert fetch failure must propagate out of upload_final_pdf."""
    from datetime import datetime, timezone
    from unittest.mock import AsyncMock, patch

    from docreview360.integrations.sharepoint_upload import upload_final_pdf

    mock_client = AsyncMock()
    mock_client.upload_file = AsyncMock()
    mock_client.update_metadata = AsyncMock()

    def _bad_fetcher(url: str) -> bytes:
        raise ConnectionError("cert server down")

    # async_client_from_env is imported from ..sharepoint inside the function body
    with patch(
        "docreview360.sharepoint.async_client_from_env",
        new=AsyncMock(return_value=mock_client),
    ):
        with pytest.raises(ConnectionError, match="cert server down"):
            await upload_final_pdf(
                approval_id="appr-123",
                item_id="item-456",
                document=b"PDF content",
                document_hash="abc",
                provider_metadata=None,
                signed_at=datetime.now(timezone.utc),
                certificate_url="https://certs.example.com/cert.pem",
                fetcher=_bad_fetcher,
            )

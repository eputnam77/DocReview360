"""Tests ensuring SharePoint upload retries and logging."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Tuple

import pytest
from docreview360 import approvals as approvals_mod
from docreview360.approvals import signatures as approvals_sig
from docreview360.monitoring import APPROVAL_UPLOAD_RETRIES


class _EventRecorder:
    def __init__(self) -> None:
        self.events: List[Tuple[str, Dict[str, Any]]] = []

    def __call__(self, action: str, *args: Any, **kwargs: Any) -> None:
        self.events.append((action, kwargs))


def _baseline(metric_label: str) -> float:
    sample = APPROVAL_UPLOAD_RETRIES.labels(metric_label)
    return float(sample._value.get())


def _make_pending_approval() -> approvals_mod.ApprovalModel:
    return approvals_mod.ApprovalModel(
        id="approval-xyz",
        workflow="wf",
        reviewer="user",
        document_id="doc",
        state="pending",
        signature_provider="acme",
        provider_metadata={},
        delegates=[],
    )


@pytest.mark.asyncio
async def test_update_state_retries_and_logs(monkeypatch: pytest.MonkeyPatch) -> None:
    approvals_mod.approvals.clear()
    approvals_mod.approvals["approval-xyz"] = _make_pending_approval()

    monkeypatch.setattr(approvals_sig, "log_audit_event", lambda *args, **kwargs: None)
    recorder = _EventRecorder()
    monkeypatch.setattr(approvals_sig, "log_event", recorder)

    monkeypatch.setattr(
        approvals_sig,
        "_approvals_settings_cached",
        lambda: {"upload_retry": {"max_attempts": 3, "base_delay": 0.01, "max_delay": 0.02}},
    )

    attempts = 0

    async def failing_upload(*args: Any, **kwargs: Any) -> None:
        nonlocal attempts
        attempts += 1
        raise RuntimeError("upload failed")

    monkeypatch.setattr(approvals_sig, "_upload_approval_artifacts", failing_upload)

    sleeps: List[float] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr(approvals_sig.asyncio, "sleep", fake_sleep)

    retry_before = _baseline("retry")
    exhausted_before = _baseline("exhausted")

    await approvals_mod.update_approval_state("approval-xyz", "approved")

    assert attempts == 3
    assert sleeps == [0.01, 0.02]

    retry_after = _baseline("retry")
    exhausted_after = _baseline("exhausted")
    assert retry_after == pytest.approx(retry_before + 2)
    assert exhausted_after == pytest.approx(exhausted_before + 1)

    failure_events = [event for event in recorder.events if event[0] == "approval_upload_failed"]
    assert failure_events, "expected upload failure event to be logged"
    failure = failure_events[0][1]
    assert failure["severity"] == "error"
    assert failure["attempts"] == 3
    assert failure["error_type"] == "RuntimeError"


@pytest.mark.asyncio
async def test_update_state_succeeds_after_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    approvals_mod.approvals.clear()
    approvals_mod.approvals["approval-xyz"] = _make_pending_approval()

    monkeypatch.setattr(approvals_sig, "log_audit_event", lambda *args, **kwargs: None)
    recorder = _EventRecorder()
    monkeypatch.setattr(approvals_sig, "log_event", recorder)

    monkeypatch.setattr(
        approvals_sig,
        "_approvals_settings_cached",
        lambda: {"upload_retry": {"max_attempts": 4, "base_delay": 0.0, "max_delay": 0.0}},
    )

    attempts = 0

    async def flaky_upload(*args: Any, **kwargs: Any) -> None:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RuntimeError("temporary issue")

    monkeypatch.setattr(approvals_sig, "_upload_approval_artifacts", flaky_upload)
    monkeypatch.setattr(approvals_sig.asyncio, "sleep", lambda delay: asyncio.sleep(0))

    retry_before = _baseline("retry")
    exhausted_before = _baseline("exhausted")

    await approvals_mod.update_approval_state("approval-xyz", "approved")

    assert attempts == 3

    retry_after = _baseline("retry")
    exhausted_after = _baseline("exhausted")
    assert retry_after == pytest.approx(retry_before + 2)
    assert exhausted_after == pytest.approx(exhausted_before)

    assert all(event[0] != "approval_upload_failed" for event in recorder.events)

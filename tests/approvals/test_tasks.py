"""Tests for reminder and escalation background tasks."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from docreview360 import approvals as approvals_mod
from docreview360.approvals import routing as approvals_routing


class _EventRecorder:
    def __init__(self) -> None:
        self.events: List[Tuple[str, Dict[str, Any]]] = []

    def __call__(self, action: str, *args: Any, **kwargs: Any) -> None:
        self.events.append((action, kwargs))


def _make_approval(state: str = "pending") -> approvals_mod.ApprovalModel:
    return approvals_mod.ApprovalModel(
        id="approval-1",
        workflow="workflow-1",
        reviewer="reviewer-1",
        document_id="doc-1",
        state=state,
        signature_provider="acme",
        provider_metadata={},
        delegates=[],
    )


def test_reminder_task_warns_when_missing(monkeypatch: Any) -> None:
    approvals_mod.approvals.clear()
    recorder = _EventRecorder()
    monkeypatch.setattr(approvals_routing, "log_event", recorder)

    approvals_mod._reminder_task("missing")

    assert ("approval_reminder", {}) not in recorder.events
    skipped = [event for event in recorder.events if event[0] == "approval_reminder_skipped"]
    assert skipped, "expected reminder task to log skip event"
    assert skipped[0][1]["severity"] == "warning"
    assert skipped[0][1]["reason"] == "missing_approval"


def test_escalation_task_skips_non_pending(monkeypatch: Any) -> None:
    approvals_mod.approvals.clear()
    approvals_mod.approvals["approval-1"] = _make_approval(state="approved")
    recorder = _EventRecorder()
    monkeypatch.setattr(approvals_routing, "log_event", recorder)

    approvals_mod._escalation_task("approval-1", target="owner@example.com")

    skipped = [event for event in recorder.events if event[0] == "approval_escalated_skipped"]
    assert skipped, "expected escalation to log skip event for approved approvals"
    details = skipped[0][1]
    assert details["reason"] == "approval_not_pending"
    assert details["state"] == "approved"
    assert all(event[0] != "approval_escalated" for event in recorder.events)


def test_escalation_task_logs_for_pending(monkeypatch: Any) -> None:
    approvals_mod.approvals.clear()
    approvals_mod.approvals["approval-1"] = _make_approval(state="pending")
    recorder = _EventRecorder()
    monkeypatch.setattr(approvals_routing, "log_event", recorder)

    approvals_mod._escalation_task("approval-1", target="ops@example.com")

    actions = {action for action, _ in recorder.events}
    assert "approval_escalated" in actions
    assert "approval_escalated_skipped" not in actions

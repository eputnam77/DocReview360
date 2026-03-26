import asyncio
from datetime import datetime, timezone

import pytest
from docreview360.approvals import approvals, create_approval, update_approval_state
from docreview360.logs import logs
from docreview360.workflow_engine import engine
from docreview360.workflows import ApprovalStep, create_workflow, workflow_templates, workflows


def test_sequential_progression() -> None:
    approvals.clear()
    workflows.clear()
    wf = create_workflow("p", ["phase"], template="pre-coordination", mode="sequential")
    items = sorted([a for a in approvals.values() if a.workflow == wf.id], key=lambda a: a.order)
    step1, step2 = items[:2]
    assert [a.id for a in engine.active_approvals(wf.id)] == [step1.id]
    with pytest.raises(ValueError):
        asyncio.run(update_approval_state(step2.id, "approved"))
    asyncio.run(update_approval_state(step1.id, "approved"))
    assert [a.id for a in engine.active_approvals(wf.id)] == [step2.id]
    asyncio.run(update_approval_state(step2.id, "approved"))
    assert step2.state == "approved"


def test_parallel_progression() -> None:
    approvals.clear()
    workflows.clear()
    wf = create_workflow("p", ["phase"], template="pre-coordination", mode="parallel")
    items = sorted([a for a in approvals.values() if a.workflow == wf.id], key=lambda a: a.order)
    step1, step2 = items[:2]
    active_ids = {a.id for a in engine.active_approvals(wf.id)}
    assert {step1.id, step2.id}.issubset(active_ids)
    asyncio.run(update_approval_state(step2.id, "approved"))
    assert step2.state == "approved"


def test_template_validation_allows_sequential_progression() -> None:
    approvals.clear()
    workflows.clear()
    template_name = "validation-sequential"
    workflow_templates[template_name] = [
        ApprovalStep(role="alpha", description="", order=1),
        ApprovalStep(role="beta", description="", order=2),
    ]
    try:
        wf = create_workflow("project", ["draft"], template=template_name, mode="sequential")
        items = sorted(
            [a for a in approvals.values() if a.workflow == wf.id], key=lambda a: a.order
        )
        first, second = items
        assert [a.order for a in items] == [1, 2]
        asyncio.run(update_approval_state(first.id, "approved"))
        assert [a.id for a in engine.active_approvals(wf.id)] == [second.id]
    finally:
        workflow_templates.pop(template_name, None)
        approvals.clear()
        workflows.clear()


def test_template_validation_rejects_duplicate_order(monkeypatch: pytest.MonkeyPatch) -> None:
    approvals.clear()
    workflows.clear()
    template_name = "validation-duplicate"
    workflow_templates[template_name] = [
        ApprovalStep(role="alpha", description="", order=1),
        ApprovalStep(role="beta", description="", order=1),
    ]
    events: list[dict[str, object]] = []

    def fake_log_event(action: str, *args: object, **kwargs: object) -> None:
        events.append({"action": action, "kwargs": kwargs})

    monkeypatch.setattr("docreview360.logs.log_event", fake_log_event)
    try:
        with pytest.raises(ValueError) as excinfo:
            create_workflow("project", ["draft"], template=template_name)
        assert template_name in str(excinfo.value)
        assert any(e["action"] == "workflow_template_invalid" for e in events)
    finally:
        workflow_templates.pop(template_name, None)
        approvals.clear()
        workflows.clear()


def test_template_validation_rejects_negative_order(monkeypatch: pytest.MonkeyPatch) -> None:
    approvals.clear()
    workflows.clear()
    template_name = "validation-negative"
    workflow_templates[template_name] = [
        ApprovalStep(role="alpha", description="", order=-1),
        ApprovalStep(role="beta", description="", order=0),
    ]
    events: list[dict[str, object]] = []

    def fake_log_event(action: str, *args: object, **kwargs: object) -> None:
        events.append({"action": action, "kwargs": kwargs})

    monkeypatch.setattr("docreview360.logs.log_event", fake_log_event)
    try:
        with pytest.raises(ValueError) as excinfo:
            create_workflow("project", ["draft"], template=template_name)
        assert template_name in str(excinfo.value)
        assert "negative" in str(excinfo.value)
        assert any(e["action"] == "workflow_template_invalid" for e in events)
    finally:
        workflow_templates.pop(template_name, None)
        approvals.clear()
        workflows.clear()


def test_reminder_and_escalation() -> None:
    approvals.clear()
    logs.clear()
    now = datetime.now(timezone.utc)
    create_approval("wf1", "legal", "doc1", reminder_at=now, escalate_to="boss", escalation_at=now)
    actions = [e.action for e in logs]
    assert "approval_reminder" in actions
    assert "approval_escalated" in actions

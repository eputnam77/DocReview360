import asyncio
from datetime import datetime, timezone

import pytest

from docreview360.approvals import approvals, create_approval, update_approval_state
from docreview360.logs import logs
from docreview360.workflow_engine import engine
from docreview360.workflows import create_workflow, workflows


def test_sequential_progression() -> None:
    approvals.clear()
    workflows.clear()
    wf = create_workflow("p", ["phase"], template="pre-coordination", mode="sequential")
    items = sorted(
        [a for a in approvals.values() if a.workflow == wf.id], key=lambda a: a.order
    )
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


def test_reminder_and_escalation() -> None:
    approvals.clear()
    logs.clear()
    now = datetime.now(timezone.utc)
    create_approval("wf1", "legal", "doc1", reminder_at=now, escalate_to="boss", escalation_at=now)
    actions = [e.action for e in logs]
    assert "approval_reminder" in actions
    assert "approval_escalated" in actions

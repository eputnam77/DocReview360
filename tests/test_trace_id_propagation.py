import uuid
from typing import cast

from celery import Task
from docreview360.api import approvals as api_approvals
from docreview360.approvals import ApprovalModel, approvals
from docreview360.audit import clear_audit_log, log_audit_event
from docreview360.celery_app import echo
from docreview360.logs import TRACE_ID
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_trace_id_propagates_to_logs_and_provider(monkeypatch) -> None:
    approvals.clear()
    appr = ApprovalModel(
        id="a1",
        workflow="w1",
        reviewer="r1",
        document_id="d1",
        signature="s1",
        signature_provider="prov",
    )
    approvals[appr.id] = appr

    seen_in_provider: list[str | None] = []

    async def fake_handle_signature_return(*args, **kwargs):
        seen_in_provider.append(TRACE_ID.get())

    monkeypatch.setattr(api_approvals, "handle_signature_return", fake_handle_signature_return)

    seen_in_logs: list[str | None] = []

    def fake_log_event(action: str, **kwargs):
        seen_in_logs.append(TRACE_ID.get())

    monkeypatch.setattr(api_approvals, "log_event", fake_log_event)

    app = FastAPI()
    app.include_router(api_approvals.router)
    client = TestClient(app)
    resp = client.get(
        "/approvals/return",
        params={"signature": "s1", "approval": "a1"},
    )
    assert resp.status_code == 200
    assert seen_in_logs and seen_in_logs[0] is not None
    assert seen_in_provider and seen_in_provider[0] == seen_in_logs[0]
    uuid.UUID(seen_in_logs[0])


def test_celery_task_receives_trace_id(monkeypatch) -> None:
    recorded: list[tuple[str, str | None]] = []

    def fake_log_event(action: str, **kwargs):
        recorded.append((action, TRACE_ID.get()))

    monkeypatch.setattr("docreview360.celery_app.log_event", fake_log_event)
    TRACE_ID.set("tid123")
    cast(Task, echo).delay("hello")
    assert ("task_started", "tid123") in recorded
    assert ("task_succeeded", "tid123") in recorded


def test_audit_log_event_includes_trace_id(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("docreview360.audit._AUDIT_LOG_PATH", tmp_path / "audit.log")
    TRACE_ID.set("audit123")
    entry = log_audit_event("doc", "evt")
    assert entry.context["trace_id"] == "audit123"
    clear_audit_log()

from __future__ import annotations

import importlib

import pytest

from docreview360 import event_dispatcher


class DummyWorkflow:
    id = "wf1"
    phase = "done"
    phases = ["start", "done"]
    callback_url = "http://callback"

    def model_dump(self) -> dict[str, object]:
        return {"id": self.id, "phase": self.phase, "phases": self.phases}


def test_dispatcher_sends_on_status_change(monkeypatch):
    sent: dict[str, object] = {}

    def fake_post(url: str, **kwargs: object):
        sent["url"] = url
        sent["json"] = kwargs.get("json")

        class Resp:
            status_code = 200

        return Resp()

    monkeypatch.setattr(event_dispatcher, "http_post", fake_post)

    event_dispatcher.dispatch_workflow_event(DummyWorkflow())
    assert sent["url"] == "http://callback"
    assert sent["json"]["event"] == "workflow.completed"
    assert sent["json"]["payload"]["id"] == DummyWorkflow.id


def test_register_callback_url(monkeypatch):
    monkeypatch.setenv("DOCREVIEW360_SKIP_SAMPLE_BOOTSTRAP", "1")
    workflows_mod = importlib.reload(importlib.import_module("docreview360.workflows"))
    monkeypatch.setattr("docreview360.logs.log_event", lambda *a, **k: None)
    workflows_mod.workflows.clear()
    wf = workflows_mod.WorkflowModel(id="wf1", project="p", phase="start", phases=["start"])
    workflows_mod.workflows[wf.id] = wf
    workflows_mod.register_callback_url(wf.id, "http://cb")
    assert workflows_mod.workflows[wf.id].callback_url == "http://cb"


def test_dead_letter_queue_on_failure(monkeypatch):
    event_dispatcher.dead_letter_queue.clear()

    calls = {"count": 0}

    def fail_post(url: str, **kwargs: object):
        calls["count"] += 1
        raise RuntimeError("boom")

    monkeypatch.setattr(event_dispatcher, "http_post", fail_post)

    dispatcher = event_dispatcher.EventDispatcher(retries=2, backoff=0)
    dispatcher.send("http://callback", "evt", {"a": 1})

    assert calls["count"] == 2
    assert event_dispatcher.dead_letter_queue[-1]["url"] == "http://callback"


def test_dispatcher_rejects_invalid_retry_count() -> None:
    with pytest.raises(ValueError):
        event_dispatcher.EventDispatcher(retries=0)
    with pytest.raises(ValueError):
        event_dispatcher.EventDispatcher(retries=-1)

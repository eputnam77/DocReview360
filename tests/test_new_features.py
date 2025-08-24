import os
import pytest

# Ensure required env var for imports
os.environ.setdefault("DOCREVIEW360_SECRET_KEY", "test")

from docreview360.cache import cache_set, cache_get, clear_cache
from docreview360.deploy import normalize_port
from docreview360.logs import clear_logs, logs
from docreview360.workflows import create_workflow, start_workflow, workflows
from docreview360.documents import documents
from docreview360.approvals import approvals


def test_cache_negative_ttl() -> None:
    clear_cache()
    cache_set("a", "b", ttl=1)
    assert cache_get("a") == "b"
    assert cache_get("missing") is None
    with pytest.raises(ValueError):
        cache_set("bad", "x", ttl=-1)


def test_cache_with_fake_client(monkeypatch) -> None:
    clear_cache()
    import types
    from docreview360 import cache as cache_module

    class FakeClient:
        def __init__(self) -> None:
            self.store: dict[str, str] = {}

        def ping(self) -> None:
            return None

        def set(self, key, value, ex=None):
            self.store[key] = value

        def get(self, key):
            return self.store.get(key)

        def flushdb(self):
            self.store.clear()

    class FakeRedis:
        @staticmethod
        def from_url(url, socket_connect_timeout, socket_timeout):
            return FakeClient()

    monkeypatch.setattr(cache_module, "_redis", types.SimpleNamespace(Redis=FakeRedis))
    monkeypatch.setattr(cache_module, "_client", None)

    client = cache_module._get_client()
    assert isinstance(client, FakeClient)
    cache_module.cache_set("k", "v")
    assert cache_module.cache_get("k") == "v"
    cache_module.clear_cache()
    assert cache_module.cache_get("k") is None


def test_normalize_port_upper_bound() -> None:
    assert normalize_port(70000) == 0
    assert normalize_port("8080") == 8080
    assert normalize_port(-5) == 0
    assert normalize_port("not-a-number") == 0


def test_start_workflow_logs_even_when_log_event_stubbed(monkeypatch) -> None:
    approvals.clear()
    workflows.clear()
    documents.clear()
    clear_logs()
    wf = create_workflow("p1", ["draft"])
    approval_ids = [a.id for a in approvals.values() if a.workflow == wf.id]
    assert approval_ids
    # monkeypatch log_event to do nothing and return None
    monkeypatch.setattr("docreview360.logs.log_event", lambda *a, **k: None)
    start_workflow(wf.id, "doc", b"content")
    assert workflows[wf.id].document is not None
    assert all(
        approvals[a_id].document_id == workflows[wf.id].document for a_id in approval_ids
    )
    assert any(e.action == "approval_doc_linked" for e in logs)

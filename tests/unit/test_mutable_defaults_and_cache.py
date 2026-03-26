import pytest
from docreview360 import cache as cache_module
from docreview360.cache import cache_delete, cache_get, cache_set, clear_cache
from docreview360.documents import DocumentModel
from docreview360.workflows import ApprovalStep, WorkflowModel


def test_cache_nonfinite_and_zero_ttl():
    clear_cache()
    with pytest.raises(ValueError):
        cache_set("k", "v", float("inf"))
    cache_set("a", "b", 0)
    assert cache_get("a") == "b"
    assert cache_get("missing") is None


class DummyClient:
    def __init__(self):
        self.store: dict[str, object] = {}

    def set(self, key, value, ex=None):
        self.store[key] = value

    def get(self, key):
        return self.store.get(key)

    def delete(self, key):
        self.store.pop(key, None)

    def flushdb(self):
        self.store.clear()


def test_cache_with_client(monkeypatch):
    client = DummyClient()
    monkeypatch.setattr(cache_module, "_get_client", lambda: client)
    cache_set("x", "y", 5)
    assert client.store["x"] == "y"
    assert cache_get("x") == "y"
    cache_delete("x")
    assert "x" not in client.store
    cache_set("u", "v")
    clear_cache()
    assert client.store == {}


def test_document_model_approval_ids_isolated():
    d1 = DocumentModel(id="1", content="one")
    d2 = DocumentModel(id="2", content="two")
    d1.approval_ids.append("A")
    assert d2.approval_ids == []


def test_workflow_model_lists_isolated():
    w1 = WorkflowModel(id="1", project="p", phase="s", phases=["s"])
    w2 = WorkflowModel(id="2", project="p", phase="s", phases=["s"])
    w1.reviewers.append("alice")
    w1.approval_steps.append(ApprovalStep(role="r", description="d", order=1))
    w1.approval_roles.append("role1")
    w1.approval_sequence.append("role1")
    assert w2.reviewers == []
    assert w2.approval_steps == []
    assert w2.approval_roles == []
    assert w2.approval_sequence == []

import types

import pytest

from docreview360 import sharepoint
from docreview360.approvals import ApprovalModel
from docreview360.sharepoint import SharePointClient

class DummyResponse:
    def __init__(self, payload):
        self._payload = payload
        self.content = b""
    def raise_for_status(self):
        pass
    def json(self):
        return self._payload


def test_list_versions_filters_non_strings(monkeypatch):
    client = SharePointClient("s","d","t")
    monkeypatch.setattr(sharepoint.requests, "get", lambda url, headers: DummyResponse({"value": [{"id": "1"}, {"id": None}, {"no": 2}, {"id": 3}]}) )
    ids = client.list_versions("item")
    assert ids == ["1", "3"]


def test_upload_with_scoring_collects_ids(monkeypatch):
    client = SharePointClient("s","d","t")
    monkeypatch.setattr(client, "upload_file", lambda path, data: "item1")
    monkeypatch.setattr(client, "set_properties", lambda item_id, metadata: None)
    monkeypatch.setattr(
        sharepoint,
        "quality_assessment",
        lambda text: types.SimpleNamespace(score=0.4, raw_score=0.4, flags=(0.2, 0.1, 0.05)),
    )
    approvals_list = [
        ApprovalModel(id="A1", workflow="wf", reviewer="r", document_id="item1"),
        ApprovalModel(id="A2", workflow="wf", reviewer="r", document_id="item1"),
    ]
    def fake_create(*a, **k):
        return approvals_list.pop(0)
    monkeypatch.setattr(sharepoint, "create_approval", fake_create)
    monkeypatch.setattr(sharepoint, "submit_draft_for_approval", lambda *a, **k: approvals_list[0])
    item_id, score, approvals = client.upload_with_scoring("p", b"hi", None, workflow="wf")
    assert item_id == "item1"
    assert approvals == ["A1", "A2"]

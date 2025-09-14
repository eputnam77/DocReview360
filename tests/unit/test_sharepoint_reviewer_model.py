from types import SimpleNamespace

from docreview360 import sharepoint
from docreview360.approvals import ApprovalModel
from docreview360.fann_model import Weights
from docreview360.sharepoint import SharePointClient


def test_upload_with_scoring_uses_reviewer_model(monkeypatch):
    client = SharePointClient("s", "d", "t")
    monkeypatch.setattr(client, "upload_file", lambda path, data: "item1")
    monkeypatch.setattr(client, "set_properties", lambda item_id, metadata: None)
    monkeypatch.setattr(sharepoint, "approval_likelihood", lambda text, weights: 0.6)

    def fake_submit(
        workflow,
        reviewer,
        doc_id,
        text,
        weights,
        *,
        threshold=0.5,
        extra_reviewer="policy",
        reviewer_model=None,
    ):
        assert reviewer is None
        assert reviewer_model is not None
        return ApprovalModel(id="A1", workflow=workflow, reviewer="auto", document_id=doc_id)

    monkeypatch.setattr(sharepoint, "submit_draft_for_approval", fake_submit)

    item_id, score, approvals = client.upload_with_scoring(
        "p",
        b"hi",
        Weights([[0]], [0], [0], 0),
        workflow="wf",
        reviewer=None,
        reviewer_model=SimpleNamespace(route_draft=lambda text: "auto"),
    )
    assert item_id == "item1"
    assert approvals == ["A1"]

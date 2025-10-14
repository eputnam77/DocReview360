from types import SimpleNamespace

from docreview360 import sharepoint
from docreview360.approvals import ApprovalModel
from docreview360.sharepoint import SharePointClient


def test_upload_with_scoring_uses_reviewer_model(monkeypatch):
    client = SharePointClient("s", "d", "t")
    monkeypatch.setattr(client, "upload_file", lambda path, data: "item1")
    monkeypatch.setattr(client, "set_properties", lambda item_id, metadata: None)
    monkeypatch.setattr(
        sharepoint,
        "quality_assessment",
        lambda text: SimpleNamespace(score=0.6, raw_score=0.6, flags=(0.1, 0.2, 0.3)),
    )

    def fake_submit(
        workflow,
        reviewer,
        doc_id,
        text,
        critic,
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
        None,
        workflow="wf",
        reviewer=None,
        reviewer_model=SimpleNamespace(route_draft=lambda text: "auto"),
    )
    assert item_id == "item1"
    assert approvals == ["A1"]

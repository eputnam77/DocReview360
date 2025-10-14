import pytest
from datetime import datetime, timedelta, timezone
from docreview360 import approvals
from docreview360.approvals import ReviewerModel, ApprovalModel
from docreview360.ml.torch_models import build_clarity_critic


class DummyModel(ReviewerModel):
    def route_draft(self, text: str) -> str | None:  # type: ignore[override]
        return None


def test_submit_draft_requires_reviewer_model_when_missing():
    with pytest.raises(ValueError):
        approvals.submit_draft_for_approval("wf", None, "doc", "text", build_clarity_critic())


def test_submit_draft_reviewer_model_returns_none():
    model = DummyModel()
    with pytest.raises(ValueError):
        approvals.submit_draft_for_approval("wf", None, "doc", "text", build_clarity_critic(), reviewer_model=model)


def test_create_approval_sets_fields(monkeypatch):
    approvals.approvals.clear()
    approval = approvals.create_approval("wf", "r", document=b"hi", delegates=["d1"], reminder_at=datetime.now(timezone.utc) + timedelta(minutes=1))
    assert approval.id in approvals.approvals
    assert approval.delegates == ["d1"]

import numpy as np
import pytest
from datetime import datetime, timedelta, timezone
from docreview360 import approvals
from docreview360.approvals import ReviewerModel, ApprovalModel
from docreview360.ml.routing_critic import ROUTING_FEATURE_NAMES
from docreview360.ml.torch_models import build_clarity_critic
from docreview360.reviewer_model import Recommendation


class DummyModel(ReviewerModel):
    def recommend(self, text: str, k: int = 3) -> Recommendation:  # type: ignore[override]
        return Recommendation(
            approval_likelihood=0.2,
            ranked_reviewers=[],
            features=np.zeros(len(ROUTING_FEATURE_NAMES), dtype=np.float32),
        )


def test_submit_draft_requires_reviewer_model_when_missing():
    with pytest.raises(ValueError):
        approvals.submit_draft_for_approval("wf", None, "doc", "text", build_clarity_critic())


def test_submit_draft_reviewer_model_returns_none():
    model = DummyModel()
    with pytest.raises(ValueError):
        approvals.submit_draft_for_approval("wf", None, "doc", "text", build_clarity_critic(), reviewer_model=model)


def test_submit_draft_captures_scoring_metadata(monkeypatch):
    approvals.approvals.clear()
    events: list[tuple[str, dict]] = []

    def fake_log_event(name: str, **kwargs) -> None:
        events.append((name, kwargs))

    monkeypatch.setattr(approvals, "log_event", fake_log_event)

    model = ReviewerModel()
    text = "Highly structured document with metadata"
    expected = model.recommend(text).approval_likelihood
    approvals.approvals.clear()

    approval = approvals.submit_draft_for_approval(
        "wf",
        None,
        "doc42",
        text,
        build_clarity_critic(),
        reviewer_model=model,
        threshold=0.8,
    )

    assert approval.reviewer == "bob"
    assert "approval_likelihood" in approval.scoring_metadata
    assert approval.scoring_metadata["approval_likelihood"] == pytest.approx(expected)
    assert len(approval.scoring_metadata["recommendations"]) >= 1
    assert sum(1 for name in approvals.approvals.values() if name.workflow == "wf") == 2

    logged = [payload for event, payload in events if event == "reviewer_recommendation"]
    assert logged
    assert logged[0]["recommendations"][0]["reviewer"] == "bob"


def test_create_approval_sets_fields(monkeypatch):
    approvals.approvals.clear()
    approval = approvals.create_approval("wf", "r", document=b"hi", delegates=["d1"], reminder_at=datetime.now(timezone.utc) + timedelta(minutes=1))
    assert approval.id in approvals.approvals
    assert approval.delegates == ["d1"]

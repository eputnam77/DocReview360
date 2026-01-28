from __future__ import annotations

import pytest

from docreview360.reviewer_model import ReviewerModel


def test_reviewer_model_anomaly_detection() -> None:
    model = ReviewerModel()
    # Reviewer A approves everything, B rejects everything, C is mixed
    for decision in [True, True]:
        model.record_decision("A", decision)
    for decision in [False, False]:
        model.record_decision("B", decision)
    model.record_decision("C", True)
    model.record_decision("C", False)

    assert model.approval_rate("A") == 1.0
    assert model.approval_rate("B") == 0.0
    anomalies = model.anomalous_reviewers(threshold=0.2)
    assert set(anomalies) == {"A", "B"}


def test_reviewer_model_recommend_validates_k() -> None:
    model = ReviewerModel()

    with pytest.raises(TypeError):
        model.recommend("Quick draft", k=True)

    with pytest.raises(ValueError):
        model.recommend("Quick draft", k=0)

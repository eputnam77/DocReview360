import math

import pytest

from docreview360.ml.torch_models import build_risk_critic
from docreview360.review_analytics import (
    LessonsRepository,
    ReviewTrends,
    benchmark_document,
    detect_anomalous_document,
)


def test_lessons_and_trends_basic() -> None:
    repo = LessonsRepository()
    repo.add("p1", "l1")
    repo.add("p1", "l2")
    assert repo.aggregate()["p1"] == ["l1", "l2"]

    trends = ReviewTrends()
    trends.add("p1", 0.5)
    trends.add("p1", 0.7)
    assert trends.trend("p1") == [0.5, 0.7]
    assert trends.moving_average("p1", window=2) == [0.6]


def test_review_analytics_helpers() -> None:
    # benchmark_document handles empty gold set
    assert benchmark_document("text", []) == 0.0
    assert benchmark_document("a", ["a", "b"]) > 0

    critic = build_risk_critic()
    critic.reset_parameters("zeros")
    anomalous, score = detect_anomalous_document("sample", critic, [])
    assert anomalous is False and math.isfinite(score)
    history = [score + 0.5, score + 0.5]
    anomalous2, _ = detect_anomalous_document("sample", critic, history)
    assert anomalous2 is True


def test_moving_average_empty() -> None:
    trends = ReviewTrends()
    assert trends.moving_average("p", window=2) == []
    trends.add("p", 0.5)
    with pytest.raises(ValueError):
        trends.moving_average("p", window=0)

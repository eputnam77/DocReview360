import pytest

from docreview360.reviewer_model import ReviewerModel


def test_recommendations_are_deterministic() -> None:
    model = ReviewerModel()
    text = "Highly structured document with clear headings and orderly layout."

    first = model.recommend(text, k=3)
    second = model.recommend(text, k=3)

    assert first.ranked_reviewers == second.ranked_reviewers
    assert first.primary == "bob"
    assert pytest.approx(first.approval_likelihood, rel=1e-6) == second.approval_likelihood
    assert pytest.approx(sum(prob for _, prob in first.ranked_reviewers), rel=1e-6) == 1.0


def test_latency_buckets_increment() -> None:
    model = ReviewerModel()
    baseline = model.latency_buckets.copy()

    for _ in range(3):
        model.recommend("Quick draft")

    updated = model.latency_buckets
    assert updated["<10ms"] == baseline["<10ms"] + 3


def test_reviewer_feedback_updates() -> None:
    model = ReviewerModel()
    model.record_decision("alice", True)
    model.record_decision("alice", False)
    model.record_decision("bob", True)

    feedback = model.reviewer_feedback
    assert feedback["alice"] == {"approved": 1, "rejected": 1}
    assert feedback["bob"]["approved"] == 1
    assert model.consistency_score("alice") == 0.0

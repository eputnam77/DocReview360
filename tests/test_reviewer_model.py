from docreview360.reviewer_model import ReviewerModel


def _zero_weights():
    from docreview360.fann_model import Weights

    return Weights([[0.0] * 6 for _ in range(4)], [0.0] * 4, [0.0] * 4, 0.0)


def test_reviewer_model_basic():
    model = ReviewerModel()
    text = "Sample content for review."
    model.update_preferences("alice", text)
    model.record_decision("alice", True)
    model.record_decision("alice", True)
    assert model.consistency_score("alice") == 1.0
    assert model.route_draft(text) == "alice"


def test_profiles_survive_round_trip(tmp_path):
    model = ReviewerModel()
    text = "Content for serialization test."
    model.update_preferences("bob", text)
    model.record_decision("bob", True)
    model.record_decision("bob", False)

    path = tmp_path / "profiles.json"
    model.save(path)

    new_model = ReviewerModel()
    new_model.load(path)

    assert new_model._profiles == model._profiles


def test_submit_draft_routes_highest_preference():
    from docreview360.approvals import approvals, submit_draft_for_approval

    approvals.clear()
    model = ReviewerModel()
    text = "repeat repeat"
    model.update_preferences("alice", text)
    model.update_preferences("bob", "unique words here")
    weights = _zero_weights()
    approval = submit_draft_for_approval(
        "wf", None, "doc1", text, weights, reviewer_model=model
    )
    assert approval.reviewer == "alice"

    # Bob learns preference for repeated text, becoming top choice
    model.update_preferences("bob", text)
    model.update_preferences("bob", text)
    approval2 = submit_draft_for_approval(
        "wf2", None, "doc2", text, weights, reviewer_model=model
    )
    assert approval2.reviewer == "bob"


def test_anomalous_reviewers_ignore_no_decisions() -> None:
    """Reviewers without decisions should not be flagged as anomalous."""
    model = ReviewerModel()
    model.update_preferences("alice", "text")
    model.record_decision("alice", True)
    model.record_decision("alice", False)
    model.update_preferences("bob", "text")  # no decisions recorded
    reviewers = model.anomalous_reviewers()
    assert "bob" not in reviewers

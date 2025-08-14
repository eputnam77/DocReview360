from docreview360.reviewer_model import ReviewerModel


def test_reviewer_model_basic():
    model = ReviewerModel()
    text = "Sample content for review."
    model.update_preferences("alice", text)
    model.record_decision("alice", True)
    model.record_decision("alice", True)
    assert model.consistency_score("alice") == 1.0
    assert model.route_draft(text) == "alice"

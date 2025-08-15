from docreview360.reviewer_model import ReviewerModel


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

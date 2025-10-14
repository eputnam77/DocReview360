from docreview360 import ai_utils
from docreview360.ai_utils import (
    FANN_FEATURE_NAMES,
    _fann_features,
    structural_pattern_score,
    style_guide_score,
)
from docreview360.ml.torch_models import build_clarity_critic, train_critic, update_critic


def test_style_and_structure_features(monkeypatch) -> None:
    # Ensure heuristics are used even if GovDocVerify is installed
    monkeypatch.setattr(ai_utils, "_gov_run", None)
    good_style = "This is a sentence. Another one."
    bad_style = "bad sentence. another."
    repeat = "This is is wrong."
    assert style_guide_score(good_style) > style_guide_score(bad_style)
    assert style_guide_score(good_style) > style_guide_score(repeat)
    long = "This is a very long sentence that should trigger the length rule " * 5 + "."
    assert style_guide_score(good_style) > style_guide_score(long)

    structured = "# H\ntext\n# H2\nmore"
    bulleted = "- item\n- item2"
    plain = "plain\ntext"
    bad_heading = "# H1\n#### jump\ntext"
    idx = FANN_FEATURE_NAMES.index("structure")
    assert structural_pattern_score(structured) > structural_pattern_score(plain)
    assert structural_pattern_score(bulleted) > structural_pattern_score(plain)
    assert _fann_features(structured)[idx] > _fann_features(plain)[idx]
    assert structural_pattern_score(structured) > structural_pattern_score(bad_heading)


def test_update_model_changes_weights() -> None:
    critic = build_clarity_critic()
    train_critic(critic, ["ok", "bad bad"], [0, 1], epochs=40, lr=0.05)
    before = critic.predict("bad bad")
    update_critic(critic, ["bad bad bad"], [1], epochs=30, lr=0.05)
    after = critic.predict("bad bad")
    assert after != before

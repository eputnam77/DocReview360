import docreview360.ai_utils as ai_utils
from docreview360.ai_utils import (
    FANN_FEATURE_NAMES,
    _fann_features,
    structural_pattern_score,
    style_guide_score,
)
from docreview360.fann_model import train_model, update_model


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
    base = train_model(["ok", "bad bad"], [0, 1], epochs=2)
    updated = update_model(base, ["bad bad bad"], [1], epochs=2)
    assert updated != base

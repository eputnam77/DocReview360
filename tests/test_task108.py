from docreview360.ai_utils import (
    FANN_FEATURE_NAMES,
    _fann_features,
    structural_pattern_score,
    style_guide_score,
)
from docreview360.fann_model import train_model, update_model


def test_style_and_structure_features() -> None:
    good_style = "This is a sentence. Another one."
    bad_style = "bad sentence. another."
    assert style_guide_score(good_style) > style_guide_score(bad_style)

    structured = "# H\ntext\n# H2\nmore"
    plain = "plain\ntext"
    idx = FANN_FEATURE_NAMES.index("structure")
    assert structural_pattern_score(structured) > structural_pattern_score(plain)
    assert _fann_features(structured)[idx] > _fann_features(plain)[idx]


def test_update_model_changes_weights() -> None:
    base = train_model(["ok", "bad bad"], [0, 1], epochs=2)
    updated = update_model(base, ["bad bad bad"], [1], epochs=2)
    assert updated != base

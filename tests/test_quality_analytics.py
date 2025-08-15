from pathlib import Path

from docreview360.ai_utils import style_guide_score
from docreview360.quality import high_risk_warnings, initialize_high_risk_terms
from docreview360.review_analytics import estimate_review_effort


def test_quality_and_effort() -> None:
    text = "This is an urgent report."
    assert "urgent" in high_risk_warnings(text)
    assert estimate_review_effort(text) > 0


def test_custom_high_risk_terms(tmp_path: Path) -> None:
    terms_file = tmp_path / "custom_terms.json"
    terms_file.write_text('["hazard"]')
    initialize_high_risk_terms(terms_file)
    assert high_risk_warnings("Hazard detected") == ["hazard"]
    initialize_high_risk_terms()  # reset to default


def test_style_guide_new_checks() -> None:
    good = "This is fine, indeed; correct."
    missing_comma = "This is wrong,indeed."  # missing space after comma
    missing_semicolon = "This is wrong;also incorrect."  # missing space after semicolon
    trailing_ws = "This line is fine. \nAnother line."  # trailing whitespace before newline
    repeated_caps = "THis has bad caps."  # repeated capitalization

    base = style_guide_score(good)
    assert base > style_guide_score(missing_comma)
    assert base > style_guide_score(missing_semicolon)
    assert base > style_guide_score(trailing_ws)
    assert base > style_guide_score(repeated_caps)

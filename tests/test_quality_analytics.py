from docreview360.quality import high_risk_warnings
from docreview360.review_analytics import estimate_review_effort
from docreview360.ai_utils import style_guide_score


def test_quality_and_effort():
    text = "This is an urgent report."
    assert "urgent" in high_risk_warnings(text)
    assert estimate_review_effort(text) > 0


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

from docreview360.quality import high_risk_warnings
from docreview360.review_analytics import estimate_review_effort


def test_quality_and_effort():
    text = "This is an urgent report."
    assert "urgent" in high_risk_warnings(text)
    assert estimate_review_effort(text) > 0

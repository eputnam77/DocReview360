import pytest

from docreview360 import quality


def test_high_risk_warnings_preserves_text_order(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(quality, "_HIGH_RISK_TERMS", {"alpha", "beta"})
    text = "Beta comes first then alpha then beta again"
    assert quality.high_risk_warnings(text) == ["beta", "alpha"]

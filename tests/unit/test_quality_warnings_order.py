import pytest

from docreview360 import quality


def test_high_risk_warnings_return_sorted_terms(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(quality, "_HIGH_RISK_TERMS", {"beta", "alpha"})
    # Order should be deterministic regardless of set hashing
    assert quality.high_risk_warnings("alpha beta") == ["alpha", "beta"]

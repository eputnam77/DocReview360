from __future__ import annotations

import math

import pytest

from docreview360 import ai_utils


def test_style_guide_score_fallback(monkeypatch) -> None:
    def fail(path: str, kind: str):  # pragma: no cover - executed via style_guide_score
        raise RuntimeError("boom")

    monkeypatch.setattr(ai_utils, "_gov_run", fail)
    score = ai_utils.style_guide_score("Sentence one. Sentence two?")
    assert 0.0 <= score <= 1.0


def test_structural_pattern_score_heading_jump() -> None:
    text = "# H1\n### H3\n- bullet"
    assert math.isclose(ai_utils.structural_pattern_score(text), 0.5)


def test_detect_anomalies_rejects_invalid_threshold_type() -> None:
    with pytest.raises(TypeError):
        ai_utils.detect_anomalies("text", threshold="0.5")
    with pytest.raises(TypeError):
        ai_utils.detect_anomalies("text", threshold=True)


def test_detect_anomalies_rejects_out_of_range_threshold() -> None:
    with pytest.raises(ValueError):
        ai_utils.detect_anomalies("text", threshold=-0.1)
    with pytest.raises(ValueError):
        ai_utils.detect_anomalies("text", threshold=1.1)

from __future__ import annotations

import math

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

import importlib.util
import math
import sys
from pathlib import Path

import pytest

from docreview360.quality import QUALITY_FLAG_NAMES, explain_score, quality_assessment

_FEATURES_SPEC = importlib.util.spec_from_file_location(
    "tests.docreview360_ml_features",
    Path("src/docreview360/ml/features.py").resolve(),
)
_FEATURES_MOD = importlib.util.module_from_spec(_FEATURES_SPEC)
sys.modules[_FEATURES_SPEC.name] = _FEATURES_MOD
_FEATURES_SPEC.loader.exec_module(_FEATURES_MOD)

_SCORE_WEIGHTS = [0.8, -0.2, -0.5, 1.1, 0.6, 0.4]
_SCORE_BIAS = 0.1
_FLAG_WEIGHTS = [
    [0.5, -0.3, 0.1],
    [-0.2, 0.4, -0.6],
    [0.7, 0.6, -0.5],
    [-0.1, -0.2, 0.8],
    [0.3, -0.4, 0.2],
    [-0.5, 0.7, 0.3],
]
_FLAG_BIAS = [0.0, 0.1, -0.1]


def _legacy_vector(text: str) -> list[float]:
    legacy = _FEATURES_MOD.quality_features(text)["legacy"]["fann"]
    return [legacy[name] for name in _FEATURES_MOD.FANN_FEATURE_NAMES]


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def _expected_from_fixture(text: str) -> tuple[float, list[float]]:
    features = _legacy_vector(text)
    linear = sum(f * w for f, w in zip(features, _SCORE_WEIGHTS)) + _SCORE_BIAS
    raw = _sigmoid(linear)
    flags = []
    for j in range(len(_FLAG_BIAS)):
        val = sum(features[i] * _FLAG_WEIGHTS[i][j] for i in range(len(features))) + _FLAG_BIAS[j]
        flags.append(_sigmoid(val))
    return raw, flags


def test_quality_assessment_matches_onnx_fixture() -> None:
    text = "This memorandum is well structured and easy to follow."
    assessment = quality_assessment(text)
    expected_raw, expected_flags = _expected_from_fixture(text)

    assert assessment.raw_score == pytest.approx(expected_raw, rel=1e-6)
    assert assessment.score == pytest.approx(expected_raw, rel=1e-6)
    assert assessment.flags == pytest.approx(expected_flags, rel=1e-6)
    assert len(assessment.flags) == len(QUALITY_FLAG_NAMES)


def test_quality_assessment_penalises_high_risk_terms() -> None:
    text = "URGENT notice repeated repeated repeated repeated."
    assessment = quality_assessment(text)
    expected_raw, _ = _expected_from_fixture(text)

    assert assessment.raw_score == pytest.approx(expected_raw, rel=1e-6)
    assert assessment.score == pytest.approx(expected_raw * 0.9, rel=1e-6)
    assert assessment.score < assessment.raw_score


def test_explain_score_reports_triggered_flags() -> None:
    text = "The policy includes long sentences with repeated repeated repeated words and complex structures."
    details = explain_score(text)
    triggered = {name for name, value in details["flags"].items() if value >= 0.7}

    assert details["score"] == pytest.approx(quality_assessment(text).score, rel=1e-6)
    for flag in triggered:
        assert f"quality flag triggered: {flag}" in details["rationale"]
    # Ensure at least one rationale references high-risk when terms appear
    risky = explain_score("This URGENT update requires immediate attention.")
    assert any("high-risk" in r for r in risky["rationale"])

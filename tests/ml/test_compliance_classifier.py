from __future__ import annotations

import json
from pathlib import Path

import pytest

from docreview360.ml import clear_session_cache
from docreview360.ml.compliance_classifier import evaluate_compliance, model_path
from docreview360.ml.features import compliance_features

_FIXTURE_DIR = Path(__file__).with_name("fixtures")


def _load_text() -> str:
    return (_FIXTURE_DIR / "sample_text.txt").read_text()


def _load_metadata() -> dict[str, object]:
    return json.loads((_FIXTURE_DIR / "sample_metadata.json").read_text())


def test_classifier_returns_expected_probability_and_rules() -> None:
    text = _load_text()
    metadata = _load_metadata()
    result = evaluate_compliance(text, metadata)

    assert result.source in ("onnx", "heuristic")
    assert result.probability == pytest.approx(0.5254678, rel=1e-6, abs=1e-6)
    assert result.failing_rules == [
        "low_readability",
        "weak_structure",
        "style_inconsistency",
        "high_compliance_risk",
    ]

    features = compliance_features(text, metadata)["features"]
    assert set(result.features) == set(features)
    for name, value in features.items():
        assert result.features[name] == pytest.approx(value, rel=1e-6, abs=1e-6)


def test_classifier_falls_back_when_model_missing(tmp_path: Path) -> None:
    text = _load_text()
    metadata = _load_metadata()
    original = model_path()
    backup = tmp_path / original.name
    clear_session_cache()
    original.rename(backup)
    try:
        result = evaluate_compliance(text, metadata)
    finally:
        clear_session_cache()
        backup.rename(original)

    assert result.source == "heuristic"
    assert result.probability == pytest.approx(0.5254678, rel=1e-6, abs=1e-6)

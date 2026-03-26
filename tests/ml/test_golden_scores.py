from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from docreview360.ml.compliance_classifier import (
    compliance_model_metadata,
    evaluate_compliance,
)
from docreview360.ml.features import (
    SIGNATURE_ANOMALY_FEATURE_NAMES,
    compliance_features,
    routing_features,
    signature_features,
)
from docreview360.ml.golden_fixtures import generate_golden_fixtures
from docreview360.ml.onnx_infer import metadata_to_context
from docreview360.ml.signature_anomaly import score_signature_anomaly
from docreview360.reviewer_model import ReviewerModel

_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "data" / "ml"


def _load_fixture(name: str) -> dict[str, object]:
    return json.loads((_FIXTURE_DIR / name).read_text())


def _assert_mapping(actual: dict[str, float], expected: dict[str, float]) -> None:
    assert set(actual) == set(expected)
    for key, value in expected.items():
        assert actual[key] == pytest.approx(value, rel=1e-6, abs=1e-6)


def test_compliance_fixture_matches_runtime() -> None:
    fixture = _load_fixture("compliance.json")
    text = fixture["input"]["text"]  # type: ignore[index]
    metadata = fixture["input"]["metadata"]  # type: ignore[index]

    payload = compliance_features(text, metadata)
    _assert_mapping(payload["features"], fixture["features"]["features"])  # type: ignore[index]

    result = evaluate_compliance(text, metadata)
    assert result.probability == pytest.approx(fixture["probability"], rel=1e-6)
    assert result.failing_rules == fixture["failing_rules"]
    assert result.source == fixture["source"]

    meta = metadata_to_context(compliance_model_metadata()) or {}
    expected_model = fixture["model"]  # type: ignore[index]
    if expected_model:
        assert meta.get("sha256") == expected_model.get("sha256")


def test_routing_fixture_matches_recommendations() -> None:
    fixture = _load_fixture("routing.json")
    text = fixture["input"]["text"]  # type: ignore[index]
    metadata = fixture["input"]["metadata"]  # type: ignore[index]

    payload = routing_features(text, metadata)
    _assert_mapping(payload["features"], fixture["features"]["features"])  # type: ignore[index]

    model = ReviewerModel()
    recommendation = model.recommend(text, k=len(fixture["recommendation"]["ranked_reviewers"]))  # type: ignore[index]
    assert recommendation.approval_likelihood == pytest.approx(
        fixture["recommendation"]["approval_likelihood"], rel=1e-6
    )
    actual_probs = [prob for _, prob in recommendation.ranked_reviewers]
    expected_probs = [
        entry["probability"] for entry in fixture["recommendation"]["ranked_reviewers"]
    ]  # type: ignore[index]
    np.testing.assert_allclose(actual_probs, expected_probs, rtol=1e-6, atol=1e-6)

    meta = metadata_to_context(model.model_metadata)
    expected_model = fixture["model"]  # type: ignore[index]
    if expected_model:
        assert meta["sha256"] == expected_model["sha256"]


def test_signature_fixture_matches_score() -> None:
    fixture = _load_fixture("signature.json")
    text = fixture["input"]["text"]  # type: ignore[index]
    metadata = fixture["input"]["metadata"]  # type: ignore[index]
    retries = fixture["input"]["retries"]  # type: ignore[index]
    duration = fixture["input"]["verification_duration"]  # type: ignore[index]

    payload = signature_features(
        text,
        metadata,
        verification_duration=duration,
        retries=retries,
    )
    _assert_mapping(payload["features"], fixture["features"]["features"])  # type: ignore[index]

    vector = [payload["features"][name] for name in SIGNATURE_ANOMALY_FEATURE_NAMES]
    score, meta = score_signature_anomaly(vector)
    assert score == pytest.approx(fixture["score"], rel=1e-6)
    expected_model = fixture["model"]  # type: ignore[index]
    assert metadata_to_context(meta)["sha256"] == expected_model["sha256"]


def test_fixture_regeneration_is_idempotent(tmp_path: Path) -> None:
    generated = generate_golden_fixtures(tmp_path)
    for name, path in generated.items():
        original_data = json.loads((_FIXTURE_DIR / name).read_text())
        regenerated = json.loads(path.read_text())
        expected_model = original_data.get("model")
        if isinstance(expected_model, dict) and not expected_model:
            regenerated["model"] = {}
        assert regenerated == original_data
        if isinstance(expected_model, dict) and expected_model.get("sha256"):
            assert regenerated["model"]["sha256"] == expected_model["sha256"]

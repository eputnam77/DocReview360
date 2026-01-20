from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_FEATURES_PATH = Path(__file__).resolve().parents[2] / "src/docreview360/ml/features.py"
_SPEC = importlib.util.spec_from_file_location("docreview360.ml.features", _FEATURES_PATH)
_FEATURES = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _FEATURES  # type: ignore[index]
_SPEC.loader.exec_module(_FEATURES)  # type: ignore[union-attr]

FEATURE_SCHEMA_REGISTRY = _FEATURES.FEATURE_SCHEMA_REGISTRY
FANN_FEATURE_NAMES = _FEATURES.FANN_FEATURE_NAMES
compliance_features = _FEATURES.compliance_features
quality_features = _FEATURES.quality_features
routing_features = _FEATURES.routing_features
signature_features = _FEATURES.signature_features

try:  # pragma: no cover - optional dependency
    import jsonschema
except Exception:  # pragma: no cover - fallback validation
    jsonschema = None

_FIXTURE_DIR = Path(__file__).with_name("fixtures")
_GOLDEN_DIR = Path(__file__).resolve().parents[1] / "data" / "ml"


def _load_text() -> str:
    return (_FIXTURE_DIR / "sample_text.txt").read_text()


def _load_metadata() -> dict[str, object]:
    return json.loads((_FIXTURE_DIR / "sample_metadata.json").read_text())


def _validate_schema(name: str, payload: dict[str, object]) -> None:
    schema_path = Path(FEATURE_SCHEMA_REGISTRY[name].schema_path)
    schema = json.loads(schema_path.read_text())
    if jsonschema is not None:  # pragma: no cover - exercised in CI
        jsonschema.validate(payload, schema)
        return
    # Minimal structural check when jsonschema isn't available.
    required = schema.get("required", [])
    for key in required:
        assert key in payload
    features = payload.get("features", {})
    assert isinstance(features, dict)
    required_features = schema["properties"]["features"].get("required", [])
    for key in required_features:
        assert key in features
        value = features[key]
        assert isinstance(value, (int, float))
        assert 0.0 <= value <= 1.0


def _load_golden(name: str) -> dict[str, object]:
    return json.loads((_GOLDEN_DIR / name).read_text())


def _assert_approx_mapping(
    actual: dict[str, float], expected: dict[str, float], *, rel: float = 1e-6, abs_: float = 1e-6
) -> None:
    assert set(actual) == set(expected)
    for key, value in expected.items():
        assert actual[key] == pytest.approx(value, rel=rel, abs=abs_)


def test_quality_features_align_with_golden_fixture() -> None:
    text = _load_text()
    metadata = _load_metadata()
    payload = quality_features(text, metadata)
    assert payload == quality_features(text, metadata)
    golden = _load_golden("quality.json")

    _validate_schema("quality", payload)

    expected_features = golden["features"]["features"]  # type: ignore[index]
    expected_legacy = golden["features"]["legacy"]["fann"]  # type: ignore[index]

    _assert_approx_mapping(payload["features"], expected_features)
    _assert_approx_mapping(payload["legacy"]["fann"], expected_legacy)


def test_compliance_routing_signature_features_schema_and_range() -> None:
    text = _load_text()
    metadata = _load_metadata()
    adapters = {
        "compliance": compliance_features,
        "routing": routing_features,
        "signature": signature_features,
    }
    for name, func in adapters.items():
        first = func(text, metadata)
        second = func(text, metadata)
        assert first == second
        _validate_schema(name, first)
        for value in first["features"].values():
            assert 0.0 <= value <= 1.0


def test_metadata_completeness_ignores_empty_dict() -> None:
    text = _load_text()
    metadata = {"title": "Draft", "extra": {}}
    payload = compliance_features(text, metadata)
    assert payload["features"]["metadata_completeness"] == pytest.approx(
        0.5, rel=1e-6, abs=1e-6
    )

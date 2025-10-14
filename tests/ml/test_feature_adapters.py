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


def test_quality_features_deterministic_and_legacy_alignment() -> None:
    text = _load_text()
    metadata = _load_metadata()
    first = quality_features(text, metadata)
    second = quality_features(text, metadata)
    assert first == second
    _validate_schema("quality", first)

    legacy_expected = json.loads((_FIXTURE_DIR / "quality_legacy.json").read_text())
    legacy = first["legacy"]["fann"]
    assert set(legacy) == set(FANN_FEATURE_NAMES)
    for name, expected in legacy_expected.items():
        assert legacy[name] == pytest.approx(expected, rel=1e-6, abs=1e-6)


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

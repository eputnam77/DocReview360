# SPDX-License-Identifier: MIT
"""Utilities for generating deterministic golden fixtures for ML critics."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from ..quality import quality_assessment, quality_model_metadata
from ..reviewer_model import ReviewerModel
from .compliance_classifier import (
    compliance_model_metadata,
    evaluate_compliance,
)
from .features import (
    SIGNATURE_ANOMALY_FEATURE_NAMES,
    compliance_features,
    quality_features,
    routing_features,
    signature_features,
)
from .onnx_infer import metadata_to_context
from .signature_anomaly import score_signature_anomaly

DEFAULT_FIXTURE_DIR = Path(__file__).resolve().parents[3] / "tests" / "data" / "ml"

_SAMPLE_TEXT = """\
Project Phoenix Overview

# Introduction
This policy outlines the review timeline for the Phoenix expansion project.

# Body
Teams must submit updates weekly, include risk mitigations, and track decisions.
- Provide change logs
- Capture open questions

# Conclusion
Thank you for keeping stakeholders informed.
"""

_SAMPLE_METADATA: dict[str, Any] = {
    "title": "Project Phoenix",
    "owner": "A. Smith",
    "certificate_url": "https://example.com/certs/phoenix.pdf",
    "hash": "abc123",
    "verified_at": "2024-06-01T00:00:00Z",
}

_SIGNATURE_RETRIES = {"retry": 1, "exhausted": 0}
_SIGNATURE_DURATION = 2.4


def _dump_json(data: Mapping[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _quality_fixture() -> dict[str, Any]:
    payload = quality_features(_SAMPLE_TEXT, _SAMPLE_METADATA)
    assessment = quality_assessment(_SAMPLE_TEXT)
    meta = metadata_to_context(quality_model_metadata()) or {}
    return {
        "input": {"text": _SAMPLE_TEXT, "metadata": _SAMPLE_METADATA},
        "features": payload,
        "assessment": {
            "score": assessment.score,
            "raw_score": assessment.raw_score,
            "flags": list(assessment.flags),
        },
        "model": meta,
    }


def _compliance_fixture() -> dict[str, Any]:
    payload = compliance_features(_SAMPLE_TEXT, _SAMPLE_METADATA)
    result = evaluate_compliance(_SAMPLE_TEXT, _SAMPLE_METADATA)
    meta = metadata_to_context(compliance_model_metadata()) or {}
    return {
        "input": {"text": _SAMPLE_TEXT, "metadata": _SAMPLE_METADATA},
        "features": payload,
        "probability": result.probability,
        "failing_rules": list(result.failing_rules),
        "source": result.source,
        "model": meta,
    }


def _routing_fixture() -> dict[str, Any]:
    payload = routing_features(_SAMPLE_TEXT, _SAMPLE_METADATA)
    model = ReviewerModel()
    recommendation = model.recommend(_SAMPLE_TEXT, k=3)
    meta = metadata_to_context(model.model_metadata) or {}
    return {
        "input": {"text": _SAMPLE_TEXT, "metadata": _SAMPLE_METADATA},
        "features": payload,
        "recommendation": {
            "approval_likelihood": recommendation.approval_likelihood,
            "ranked_reviewers": [
                {"reviewer": reviewer, "probability": prob}
                for reviewer, prob in recommendation.ranked_reviewers
            ],
            "feature_vector": recommendation.features.astype(float).tolist(),
        },
        "model": meta,
    }


def _signature_fixture() -> dict[str, Any]:
    payload = signature_features(
        _SAMPLE_TEXT,
        _SAMPLE_METADATA,
        verification_duration=_SIGNATURE_DURATION,
        retries=_SIGNATURE_RETRIES,
    )
    feature_vector = [float(payload["features"][name]) for name in SIGNATURE_ANOMALY_FEATURE_NAMES]
    score, metadata = score_signature_anomaly(feature_vector)
    meta = metadata_to_context(metadata) or {}
    return {
        "input": {
            "text": _SAMPLE_TEXT,
            "metadata": _SAMPLE_METADATA,
            "verification_duration": _SIGNATURE_DURATION,
            "retries": _SIGNATURE_RETRIES,
        },
        "features": payload,
        "score": score,
        "model": meta,
    }


@dataclass(frozen=True)
class FixtureDefinition:
    filename: str
    builder: Callable[[], dict[str, Any]]


_FIXTURES: tuple[FixtureDefinition, ...] = (
    FixtureDefinition("quality.json", _quality_fixture),
    FixtureDefinition("compliance.json", _compliance_fixture),
    FixtureDefinition("routing.json", _routing_fixture),
    FixtureDefinition("signature.json", _signature_fixture),
)


def generate_golden_fixtures(destination: Path | None = None) -> dict[str, Path]:
    """Generate golden fixtures under ``destination`` returning created paths."""

    dest = destination or DEFAULT_FIXTURE_DIR
    dest.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for fixture in _FIXTURES:
        path = dest / fixture.filename
        data = fixture.builder()
        path.write_text(_dump_json(data), encoding="utf-8")
        written[fixture.filename] = path
    return written


__all__ = ["generate_golden_fixtures", "DEFAULT_FIXTURE_DIR"]

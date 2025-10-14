"""Predictive quality scoring, explanations and risk warnings."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np

from .ml.features import FANN_FEATURE_NAMES, quality_features
from .ml.onnx_infer import ModelMetadata, get_model_metadata, get_session, infer as onnx_infer

_HIGH_RISK_TERMS: set[str] = set()
_HIGH_RISK_PENALTY: float = 0.9  # Multiply score by this if risky terms are present

_MODEL_PATH = Path(__file__).resolve().parent / "models" / "quality_critic.onnx"
try:
    _MODEL_METADATA = get_model_metadata(_MODEL_PATH)
except Exception:
    _MODEL_METADATA = ModelMetadata(
        path=_MODEL_PATH,
        sha256="",
        version=None,
        custom_metadata={},
    )
_FLAG_NAMES: tuple[str, ...] = tuple(
    name.strip()
    for name in (_MODEL_METADATA.custom_metadata.get("docreview360:flags") or "").split(",")
    if name.strip()
)
if not _FLAG_NAMES:
    _FLAG_NAMES = ("clarity", "accuracy", "structure")


@dataclass(frozen=True)
class QualityAssessment:
    """Container for critic outputs with high-risk penalties applied."""

    score: float
    raw_score: float
    flags: tuple[float, ...]


def initialize_high_risk_terms(path: str | Path | None = None) -> None:
    """Load high risk terms from ``path`` or bundled ``quality_terms.json``.

    Parameters
    ----------
    path:
        Optional path to a JSON file containing a list of risky terms. When
        omitted the loader falls back to the package's default configuration.
    """
    global _HIGH_RISK_TERMS
    if path is None:
        data = (Path(__file__).resolve().parent / "quality_terms.json").read_text()
    else:
        data = Path(path).read_text()

    loaded = json.loads(data)
    if not isinstance(loaded, list) or not all(isinstance(t, str) for t in loaded):
        raise ValueError("high risk terms must be a JSON list of strings")

    # Normalize the loaded terms to lowercase.  Without this a configuration
    # file containing capitalised words would never match because
    # ``high_risk_warnings`` lowercases the input text before searching.
    _HIGH_RISK_TERMS = {t.lower() for t in loaded}


initialize_high_risk_terms()

# Default feature weights for different document types.
_DOC_TYPE_WEIGHTS: dict[str, Sequence[float]] = {
    "default": [1.0] * len(FANN_FEATURE_NAMES),
    "policy_memo": [1.0, 1.0, 1.2, 1.0, 1.5, 1.3],
    "rulemaking": [1.2, 1.0, 1.0, 1.3, 1.0, 1.0],
}


def _feature_weights(doc_type: str | None) -> Sequence[float] | None:
    if doc_type is None:
        return None
    return _DOC_TYPE_WEIGHTS.get(doc_type, _DOC_TYPE_WEIGHTS["default"])


def high_risk_warnings(text: str) -> list[str]:
    """Return list of risky terms present in ``text``."""
    lower = text.lower()
    # Preserve the order in which risky terms appear in ``text`` so callers can
    # present warnings alongside the offending words.  Sorting the terms made
    # the output deterministic but lost this positional information.  Tokenise
    # the input and collect unique matches in encounter order.  Using ``findall``
    # with ``\b`` boundaries ensures substrings inside larger words do not
    # trigger false positives.
    found: list[str] = []
    for word in re.findall(r"\b\w+\b", lower):
        if word in _HIGH_RISK_TERMS and word not in found:
            found.append(word)
    return found


def _feature_vector(text: str, doc_type: str | None) -> np.ndarray:
    payload = quality_features(text)
    legacy = payload["legacy"]["fann"]
    features = np.array([legacy[name] for name in FANN_FEATURE_NAMES], dtype=np.float32)
    weights = _feature_weights(doc_type)
    if weights is not None:
        features = features * np.array(list(weights), dtype=np.float32)
    return features.reshape(1, -1)


def _fallback_quality_assessment(text: str, doc_type: str | None) -> QualityAssessment:
    payload = quality_features(text)
    legacy = payload.get("legacy", {}).get("fann", {})
    readability = float(legacy.get("readability", 0.0))
    style = float(legacy.get("style", 0.0))
    structure = float(legacy.get("structure", 0.0))
    repeated = float(legacy.get("repeated", 0.0))
    score = 1.0
    score -= 0.25 * repeated
    score -= 0.12 * max(0.4 - style, 0.0)
    score -= 0.12 * max(0.4 - structure, 0.0)
    score -= 0.15 * max(0.6 - readability, 0.0)
    raw = max(0.0, min(1.0, score))
    warnings = high_risk_warnings(text)
    if warnings:
        raw = max(0.0, raw - 0.1 * len(warnings))
    flag_map = {
        "clarity": max(0.0, min(1.0, (0.4 - readability) / 0.4)) if readability < 0.4 else 0.0,
        "accuracy": max(0.0, min(1.0, repeated)),
        "structure": 0.5 * max(0.0, min(1.0, (0.5 - structure) / 0.5)) if structure < 0.5 else 0.0,
    }
    flags = tuple(flag_map.get(name, 0.0) for name in QUALITY_FLAG_NAMES)
    return QualityAssessment(score=raw, raw_score=raw, flags=flags)


def quality_assessment(text: str, *, doc_type: str | None = None) -> QualityAssessment:
    """Run the ONNX critic returning score, raw score and flag vector."""

    try:
        session = get_session(_MODEL_PATH)
        features = _feature_vector(text, doc_type)
        score_arr, flags_arr = onnx_infer(session, {"features": features})
        raw_score = float(np.clip(score_arr.reshape(-1)[0], 0.0, 1.0))
        flags_tuple = tuple(float(v) for v in flags_arr.reshape(-1))
        score = raw_score
    except Exception:
        fallback = _fallback_quality_assessment(text, doc_type)
        raw_score = fallback.raw_score
        flags_tuple = fallback.flags
        score = fallback.raw_score
    if high_risk_warnings(text):
        score *= _HIGH_RISK_PENALTY
    return QualityAssessment(score=score, raw_score=raw_score, flags=flags_tuple)


def quality_model_metadata() -> "ModelMetadata":
    """Return cached metadata describing the quality critic model."""

    return _MODEL_METADATA


def approval_likelihood(
    text: str,
    critic: object | None = None,
    *,
    doc_type: str | None = None,
) -> float:
    """Return approval likelihood using the ONNX critic.

    The ``critic`` argument is kept for backward compatibility with existing
    call sites that still pass a :class:`TinyCritic` instance.
    """

    return quality_assessment(text, doc_type=doc_type).score


def explain_score(
    text: str,
    critic: object | None = None,
    *,
    doc_type: str | None = None,
) -> dict[str, object]:
    """Return a breakdown of the approval score with human readable rationale."""
    payload = quality_features(text)
    legacy = payload["legacy"]["fann"]
    reasons: list[str] = []
    for name in FANN_FEATURE_NAMES:
        val = legacy[name]
        if name == "repeated" and val > 0:
            reasons.append("contains repeated words")
        elif name == "style" and val < 0.7:
            reasons.append("poor style guide adherence")
        elif name == "structure" and val < 0.5:
            reasons.append("weak structural patterns")

    assessment = quality_assessment(text, doc_type=doc_type)
    for flag_name, value in zip(_FLAG_NAMES, assessment.flags):
        if value >= 0.7:
            reasons.append(f"quality flag triggered: {flag_name}")
    
    risky_terms = high_risk_warnings(text)
    if risky_terms:
        reasons.append(f"contains high-risk terms: {', '.join(risky_terms)}")

    score = approval_likelihood(text, critic, doc_type=doc_type)
    return {"score": assessment.score, "rationale": reasons, "flags": dict(zip(_FLAG_NAMES, assessment.flags))}


QUALITY_FLAG_NAMES = _FLAG_NAMES

__all__ = [
    "QUALITY_FLAG_NAMES",
    "QualityAssessment",
    "approval_likelihood",
    "explain_score",
    "high_risk_warnings",
    "initialize_high_risk_terms",
    "quality_assessment",
    "quality_model_metadata",
]

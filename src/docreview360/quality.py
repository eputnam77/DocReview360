# SPDX-License-Identifier: MIT
"""Predictive quality scoring, explanations and risk warnings."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Sequence

from .ml.features import FANN_FEATURE_NAMES, quality_features

_logger = logging.getLogger(__name__)

_HIGH_RISK_TERMS: set[str] = set()
_HIGH_RISK_PENALTY: float = 0.9  # Multiply score by this if risky terms are present

_MODEL_PATH = Path(__file__).resolve().parent / "models" / "quality_critic.onnx"

# quality_assessment() falls back to a heuristic scorer when the ONNX critic
# cannot be loaded/run.  The fallback runs on *every* assessment, so logging the
# failure on each call would flood the logs; instead we warn once per process so
# a genuinely broken or missing model is observable without spam.
_FALLBACK_WARNED = False


@dataclass(frozen=True)
class ModelMetadata:
    """Small metadata shape used even when optional ONNX dependencies are absent."""

    path: Path
    sha256: str
    version: str | None
    custom_metadata: dict[str, str]


def _file_sha256(path: Path) -> str:
    try:
        from .ml._hashing import file_sha256

        return file_sha256(path)
    except FileNotFoundError:
        return ""


def _load_model_metadata() -> ModelMetadata:
    try:
        from .ml.onnx_infer import get_model_metadata

        metadata = get_model_metadata(_MODEL_PATH)
        return ModelMetadata(
            path=metadata.path,
            sha256=metadata.sha256,
            version=metadata.version,
            custom_metadata=dict(metadata.custom_metadata),
        )
    except Exception:
        return ModelMetadata(
            path=_MODEL_PATH,
            sha256=_file_sha256(_MODEL_PATH),
            version=None,
            custom_metadata={},
        )


_MODEL_METADATA = _load_model_metadata()
if not isinstance(_MODEL_METADATA, ModelMetadata):
    _MODEL_METADATA = ModelMetadata(
        path=_MODEL_PATH,
        sha256=_file_sha256(_MODEL_PATH),
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


_WORD_BOUNDARY_RE = re.compile(r"\b\w+\b")


@lru_cache(maxsize=32)
def _high_risk_warnings_cached(text: str) -> tuple[str, ...]:
    """Cached inner implementation returning an immutable tuple."""
    lower = text.lower()
    found: list[str] = []
    for word in _WORD_BOUNDARY_RE.findall(lower):
        if word in _HIGH_RISK_TERMS and word not in found:
            found.append(word)
    return tuple(found)


def high_risk_warnings(text: str) -> list[str]:
    """Return list of risky terms present in ``text``."""
    return list(_high_risk_warnings_cached(text))


def _feature_vector(text: str, doc_type: str | None) -> Any:
    import numpy as np

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
        import numpy as np

        from .ml.onnx_infer import get_session
        from .ml.onnx_infer import infer as onnx_infer

        session = get_session(_MODEL_PATH)
        features = _feature_vector(text, doc_type)
        score_arr, flags_arr = onnx_infer(session, {"features": features})
        raw_score = float(np.clip(score_arr.reshape(-1)[0], 0.0, 1.0))
        flags_tuple = tuple(float(v) for v in flags_arr.reshape(-1))
        score = raw_score
    except Exception as exc:
        global _FALLBACK_WARNED
        if not _FALLBACK_WARNED:
            _FALLBACK_WARNED = True
            _logger.warning(
                "Quality ONNX critic unavailable at %s (%s: %s); using heuristic "
                "fallback scorer. This is logged once per process.",
                _MODEL_PATH,
                type(exc).__name__,
                exc,
            )
        fallback = _fallback_quality_assessment(text, doc_type)
        raw_score = fallback.raw_score
        flags_tuple = fallback.flags
        score = fallback.raw_score
    if high_risk_warnings(text):
        score *= _HIGH_RISK_PENALTY
    return QualityAssessment(score=score, raw_score=raw_score, flags=flags_tuple)


def quality_model_metadata() -> "ModelMetadata":
    """Return cached metadata describing the quality critic model."""

    global _MODEL_METADATA
    if not _MODEL_METADATA.sha256:
        try:
            _MODEL_METADATA = _load_model_metadata()
        except Exception:
            if not _MODEL_METADATA.sha256:
                _MODEL_METADATA = ModelMetadata(
                    path=_MODEL_PATH,
                    sha256=_file_sha256(_MODEL_PATH),
                    version=_MODEL_METADATA.version,
                    custom_metadata=_MODEL_METADATA.custom_metadata,
                )
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

    return {
        "score": assessment.score,
        "rationale": reasons,
        "flags": dict(zip(_FLAG_NAMES, assessment.flags)),
    }


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

"""Predictive quality scoring, explanations and risk warnings."""

from __future__ import annotations

from typing import Sequence

from .fann_model import Weights, predict_weighted
from .ai_utils import FANN_FEATURE_NAMES, _fann_features

_HIGH_RISK_TERMS = {"urgent", "guarantee", "liability"}

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


def approval_likelihood(text: str, weights: Weights, *, doc_type: str | None = None) -> float:
    """Return approval likelihood using the trained FANN model.

    ``doc_type`` enables adaptive weighting of features so certain checks carry
    more influence for specific document categories.
    """

    return predict_weighted(text, weights, _feature_weights(doc_type))


def explain_score(text: str, weights: Weights, *, doc_type: str | None = None) -> dict[str, object]:
    """Return a breakdown of the approval score with human readable rationale."""

    feats = _fann_features(text)
    reasons: list[str] = []
    for name, val in zip(FANN_FEATURE_NAMES, feats):
        if name == "repeated" and val > 0:
            reasons.append("contains repeated words")
        elif name == "style" and val < 0.7:
            reasons.append("poor style guide adherence")
        elif name == "structure" and val < 0.5:
            reasons.append("weak structural patterns")
    score = approval_likelihood(text, weights, doc_type=doc_type)
    return {"score": score, "rationale": reasons}


def high_risk_warnings(text: str) -> list[str]:
    """Return list of risky terms present in ``text``."""
    lower = text.lower()
    return [term for term in _HIGH_RISK_TERMS if term in lower]

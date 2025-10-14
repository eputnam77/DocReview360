"""Predictive quality scoring, explanations and risk warnings."""

from __future__ import annotations

import json
import re
from importlib import resources
from pathlib import Path
from typing import Sequence

from .ai_utils import FANN_FEATURE_NAMES, _fann_features
from .ml.torch_models import TinyCritic

_HIGH_RISK_TERMS: set[str] = set()
_HIGH_RISK_PENALTY: float = 0.9  # Multiply score by this if risky terms are present


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
        data = resources.files(__package__).joinpath("quality_terms.json").read_text()
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


def approval_likelihood(text: str, critic: TinyCritic, *, doc_type: str | None = None) -> float:
    """Return approval likelihood using the trained FANN model.

    ``doc_type`` enables adaptive weighting of features so certain checks carry
    more influence for specific document categories.
    High-risk terms automatically reduce the score by a set penalty.
    """
    score = float(critic.predict(text, _feature_weights(doc_type)))
    if high_risk_warnings(text):
        score *= _HIGH_RISK_PENALTY
    return score


def explain_score(text: str, critic: TinyCritic, *, doc_type: str | None = None) -> dict[str, object]:
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

    risky_terms = high_risk_warnings(text)
    if risky_terms:
        reasons.append(f"contains high-risk terms: {', '.join(risky_terms)}")

    score = approval_likelihood(text, critic, doc_type=doc_type)
    return {"score": score, "rationale": reasons}

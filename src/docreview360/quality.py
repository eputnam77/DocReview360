"""Predictive quality scoring and risk warnings."""

from __future__ import annotations

from .fann_model import Weights, predict

_HIGH_RISK_TERMS = {"urgent", "guarantee", "liability"}


def approval_likelihood(text: str, weights: Weights) -> float:
    """Return approval likelihood using the trained FANN model."""
    return predict(text, weights)


def high_risk_warnings(text: str) -> list[str]:
    """Return list of risky terms present in ``text``."""
    lower = text.lower()
    return [term for term in _HIGH_RISK_TERMS if term in lower]

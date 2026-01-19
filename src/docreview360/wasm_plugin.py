"""Simplified WASM plugin lint wrapper (Task 109)."""

from __future__ import annotations

from typing import Sequence

from .guardrails import evaluate_guardrails, load_guardrail_thresholds
from .ml.features import FANN_FEATURE_NAMES


def lint_text(
    text: str,
    weights: Sequence[float] | None = None,
    threshold: float | None = None,
) -> bool:
    """Return ``True`` when ``text`` satisfies the configured guardrails."""

    if weights is not None and len(weights) not in {0, len(FANN_FEATURE_NAMES)}:
        raise ValueError("weights must match feature vector length")

    thresholds = load_guardrail_thresholds()
    thresholds = thresholds.overridden(min_compliance_probability=0.0)
    if threshold is not None:
        try:
            thresholds = thresholds.overridden(min_quality_score=float(threshold))
        except (TypeError, ValueError) as exc:
            raise ValueError("threshold must be a numeric value") from exc

    diagnostics = evaluate_guardrails(text, thresholds=thresholds)
    return not diagnostics.blocked

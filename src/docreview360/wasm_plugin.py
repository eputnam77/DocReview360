"""Simplified WASM plugin lint wrapper (Task 109)."""

from __future__ import annotations

from typing import Sequence

from .ml.features import FANN_FEATURE_NAMES, quality_features


def lint_text(text: str, weights: Sequence[float], threshold: float = 0.7) -> bool:
    """Return ``True`` if ``text`` passes the quality gate."""
    legacy = quality_features(text)["legacy"]["fann"]
    feats = [legacy[name] for name in FANN_FEATURE_NAMES]
    if len(weights) != len(feats):
        raise ValueError("weights must match feature vector length")
    score = sum(w * f for w, f in zip(weights, feats))
    return score < threshold

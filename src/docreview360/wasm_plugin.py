"""Simplified WASM plugin lint wrapper (Task 109)."""

from __future__ import annotations

from typing import Sequence

from .ai_utils import _fann_features


def lint_text(text: str, weights: Sequence[float], threshold: float = 0.7) -> bool:
    """Return ``True`` if ``text`` passes the quality gate."""
    feats = _fann_features(text)
    if len(weights) != len(feats):
        raise ValueError("weights must match feature vector length")
    score = sum(w * f for w, f in zip(weights, feats))
    return score < threshold

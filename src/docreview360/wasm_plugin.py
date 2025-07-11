"""Simplified WASM plugin lint wrapper (Task 109)."""

from __future__ import annotations

from typing import Sequence

from .fann_model import predict


def lint_text(text: str, weights: Sequence[float], threshold: float = 0.7) -> bool:
    """Return ``True`` if ``text`` passes the quality gate."""
    score = predict(text, weights)
    return score < threshold

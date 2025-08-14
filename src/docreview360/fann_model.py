"""Tiny logistic model utilities for ruv-FANN tasks (107-110)."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Sequence

from .ai_utils import _fann_features

_DEF_LR = 0.1
_DEF_EPOCHS = 50


def train_model(
    texts: Sequence[str],
    labels: Sequence[int],
    *,
    epochs: int = _DEF_EPOCHS,
    lr: float = _DEF_LR,
) -> list[float]:
    """Return weight vector trained using a simple logistic regression."""
    if not texts:
        raise ValueError("training requires at least one text")
    features = [(_fann_features(t) + [1.0]) for t in texts]
    weights = [0.0 for _ in range(len(features[0]))]
    for _ in range(epochs):
        for x, y in zip(features, labels):
            z = sum(w * xi for w, xi in zip(weights, x))
            pred = 1.0 / (1.0 + math.exp(-z))
            error = pred - float(y)
            for i in range(len(weights)):
                weights[i] -= lr * error * x[i]
    return weights


def save_weights(weights: Sequence[float], path: str | Path) -> Path:
    """Write ``weights`` to ``path`` as JSON."""
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(list(weights)))
    return dest


def load_weights(path: str | Path) -> list[float]:
    """Load weight vector from ``path``."""
    data = json.loads(Path(path).read_text())
    return [float(x) for x in data]


def predict(text: str, weights: Sequence[float]) -> float:
    """Return anomaly score using ``weights``."""
    feats = _fann_features(text) + [1.0]
    z = sum(w * f for w, f in zip(weights, feats))
    return 1.0 / (1.0 + math.exp(-z))

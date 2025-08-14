"""Simple neural model utilities for ruv-FANN tasks (107-110)."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .ai_utils import _fann_features

_DEF_LR = 0.1
_DEF_EPOCHS = 50
_HIDDEN = 4


@dataclass
class Weights:
    """Container for network weights."""

    w1: list[list[float]]
    b1: list[float]
    w2: list[float]
    b2: float

    def as_dict(self) -> dict[str, object]:
        return {"w1": self.w1, "b1": self.b1, "w2": self.w2, "b2": self.b2}

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "Weights":
        return cls(
            w1=[[float(v) for v in row] for row in data["w1"]],
            b1=[float(v) for v in data["b1"]],
            w2=[float(v) for v in data["w2"]],
            b2=float(data["b2"]),
        )


def train_model(
    texts: Sequence[str],
    labels: Sequence[int],
    *,
    epochs: int = _DEF_EPOCHS,
    lr: float = _DEF_LR,
) -> Weights:
    """Train a tiny two-layer neural network and return its weights."""
    if not texts:
        raise ValueError("training requires at least one text")

    feats = [_fann_features(t) for t in texts]
    w1 = [[0.0 for _ in range(len(feats[0]))] for _ in range(_HIDDEN)]
    b1 = [0.0 for _ in range(_HIDDEN)]
    w2 = [0.0 for _ in range(_HIDDEN)]
    b2 = 0.0

    for _ in range(epochs):
        for x, y in zip(feats, labels):
            # forward
            h_raw = [sum(w * xi for w, xi in zip(row, x)) + b for row, b in zip(w1, b1)]
            h = [math.tanh(v) for v in h_raw]
            z = sum(w * hi for w, hi in zip(w2, h)) + b2
            pred = 1.0 / (1.0 + math.exp(-z))

            # backward
            err = pred - float(y)
            grad_w2 = [err * hi for hi in h]
            grad_b2 = err
            grad_h = [err * w * (1 - hi ** 2) for w, hi in zip(w2, h)]

            for j in range(_HIDDEN):
                for i in range(len(x)):
                    w1[j][i] -= lr * grad_h[j] * x[i]
                b1[j] -= lr * grad_h[j]
                w2[j] -= lr * grad_w2[j]
            b2 -= lr * grad_b2

    return Weights(w1, b1, w2, b2)


def update_model(
    weights: Weights,
    texts: Sequence[str],
    labels: Sequence[int],
    *,
    epochs: int = _DEF_EPOCHS,
    lr: float = _DEF_LR,
) -> Weights:
    """Incrementally update ``weights`` using additional training data."""

    if not texts:
        return weights

    feats = [_fann_features(t) for t in texts]
    w1 = [row[:] for row in weights.w1]
    b1 = list(weights.b1)
    w2 = list(weights.w2)
    b2 = weights.b2

    for _ in range(epochs):
        for x, y in zip(feats, labels):
            h_raw = [sum(w * xi for w, xi in zip(row, x)) + b for row, b in zip(w1, b1)]
            h = [math.tanh(v) for v in h_raw]
            z = sum(w * hi for w, hi in zip(w2, h)) + b2
            pred = 1.0 / (1.0 + math.exp(-z))

            err = pred - float(y)
            grad_w2 = [err * hi for hi in h]
            grad_b2 = err
            grad_h = [err * w * (1 - hi ** 2) for w, hi in zip(w2, h)]

            for j in range(_HIDDEN):
                for i in range(len(x)):
                    w1[j][i] -= lr * grad_h[j] * x[i]
                b1[j] -= lr * grad_h[j]
                w2[j] -= lr * grad_w2[j]
            b2 -= lr * grad_b2

    return Weights(w1, b1, w2, b2)


def save_weights(weights: Weights, path: str | Path) -> Path:
    """Write ``weights`` to ``path`` as JSON."""
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(weights.as_dict()))
    return dest


def load_weights(path: str | Path) -> Weights:
    """Load weight vector from ``path``."""
    data = json.loads(Path(path).read_text())
    return Weights.from_dict(data)


def predict_weighted(
    text: str,
    weights: Weights,
    feature_weights: Sequence[float] | None = None,
) -> float:
    """Return anomaly score applying optional feature ``feature_weights``.

    ``feature_weights`` should have the same length as the FANN feature vector
    and scales the input features before they are fed into the network.  This
    enables adaptive weighting for different document types without retraining
    the model from scratch.
    """

    x = _fann_features(text)
    if feature_weights is not None:
        x = [xi * wi for xi, wi in zip(x, feature_weights)]
    h_raw = [
        sum(w * xi for w, xi in zip(row, x)) + b
        for row, b in zip(weights.w1, weights.b1)
    ]
    h = [math.tanh(v) for v in h_raw]
    z = sum(w * hi for w, hi in zip(weights.w2, h)) + weights.b2
    return 1.0 / (1.0 + math.exp(-z))


def predict(text: str, weights: Weights) -> float:
    """Return anomaly score using ``weights``."""
    return predict_weighted(text, weights)

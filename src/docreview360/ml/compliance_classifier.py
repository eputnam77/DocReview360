"""Compliance classifier built on structural features exported as ONNX."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping

import numpy as np

from .features import compliance_features

try:  # pragma: no cover - optional dependency
    from . import onnx_infer as _onnx
except Exception:  # pragma: no cover - runtime fallback when onnxruntime missing
    _onnx = None

if TYPE_CHECKING:
    from .onnx_infer import ModelMetadata

try:  # pragma: no cover - optional dependency for re-export tooling
    import torch
    from torch import Tensor, nn
except Exception:  # pragma: no cover - allow runtime without torch
    torch = None  # type: ignore[assignment]
    Tensor = Any  # type: ignore[misc, assignment]
    nn = Any  # type: ignore[assignment]

__all__ = [
    "ComplianceClassification",
    "ComplianceMLP",
    "MODEL_FEATURE_ORDER",
    "MODEL_FILENAME",
    "evaluate_compliance",
    "model_path",
    "compliance_model_metadata",
]


MODEL_FILENAME = "compliance_mlp.onnx"
MODEL_FEATURE_ORDER: tuple[str, ...] = (
    "readability",
    "structure",
    "metadata_completeness",
    "style",
    "compliance_risk",
)

_HEURISTIC_WEIGHTS: Mapping[str, float] = {
    "readability": 1.2,
    "structure": 1.0,
    "metadata_completeness": 0.8,
    "style": 0.6,
    "compliance_risk": -1.3,
}
_HEURISTIC_BIAS = -0.1

_LOWER_THAN_RULES: tuple[tuple[str, float, str], ...] = (
    ("readability", 0.45, "low_readability"),
    ("structure", 0.55, "weak_structure"),
    ("metadata_completeness", 0.75, "metadata_incomplete"),
    ("style", 0.5, "style_inconsistency"),
)
_GREATER_THAN_RULES: tuple[tuple[str, float, str], ...] = (
    ("compliance_risk", 0.6, "high_compliance_risk"),
)


@dataclass(frozen=True)
class ComplianceClassification:
    """Structured result returned by :func:`evaluate_compliance`."""

    probability: float
    failing_rules: list[str]
    features: Mapping[str, float]
    source: str


if torch is not None:  # pragma: no cover - exercised in integration tests

    class ComplianceMLP(nn.Module):
        """Tiny MLP mirroring the ONNX runtime architecture."""

        def __init__(self) -> None:
            super().__init__()
            width = len(MODEL_FEATURE_ORDER)
            self.linear1 = nn.Linear(width, width)
            self.activation = nn.ReLU()
            self.linear2 = nn.Linear(width, 1)
            self.out = nn.Sigmoid()
            self.reset_parameters()

        def reset_parameters(self) -> None:
            with torch.no_grad():
                self.linear1.weight.copy_(torch.eye(len(MODEL_FEATURE_ORDER)))
                self.linear1.bias.zero_()
                weights = torch.tensor(
                    [[_HEURISTIC_WEIGHTS[name] for name in MODEL_FEATURE_ORDER]],
                    dtype=torch.float32,
                )
                self.linear2.weight.copy_(weights)
                self.linear2.bias.fill_(_HEURISTIC_BIAS)

        def forward(self, inputs: Tensor) -> Tensor:  # type: ignore[override]
            hidden = self.activation(self.linear1(inputs))
            logits = self.linear2(hidden)
            return self.out(logits)

else:  # pragma: no cover - fallback when torch is unavailable

    class ComplianceMLP:  # type: ignore[redeclaration]
        """Placeholder used when :mod:`torch` is not installed."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401
            raise RuntimeError("Torch is required to instantiate ComplianceMLP")


def model_path() -> Path:
    """Return the absolute path to the bundled ONNX model."""

    return Path(__file__).resolve().parent / "assets" / MODEL_FILENAME


def _feature_vector(features: Mapping[str, float]) -> np.ndarray:
    return np.array(
        [[float(features.get(name, 0.0)) for name in MODEL_FEATURE_ORDER]], dtype=np.float32
    )


def _sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1 / (1 + z)
    z = math.exp(value)
    return z / (1 + z)


def _heuristic_probability(features: Mapping[str, float]) -> float:
    linear = _HEURISTIC_BIAS
    for name, weight in _HEURISTIC_WEIGHTS.items():
        linear += weight * float(features.get(name, 0.0))
    return max(0.0, min(1.0, _sigmoid(linear)))


def _rule_violations(features: Mapping[str, float]) -> list[str]:
    failing: list[str] = []
    for name, threshold, label in _LOWER_THAN_RULES:
        if float(features.get(name, 0.0)) < threshold:
            failing.append(label)
    for name, threshold, label in _GREATER_THAN_RULES:
        if float(features.get(name, 0.0)) > threshold:
            failing.append(label)
    return failing


def _run_model(vector: np.ndarray) -> tuple[float | None, str]:
    if _onnx is not None:
        try:
            session = _onnx.get_session(model_path())
            outputs = _onnx.infer(session, {"input": vector})
            return float(outputs[0].reshape(-1)[0]), "onnx"
        except Exception:
            pass
    if torch is not None and model_path().exists():
        try:
            model = ComplianceMLP()
            model.eval()
            with torch.no_grad():
                inputs = torch.from_numpy(vector)
                outputs = model(inputs)
            return float(outputs.reshape(-1)[0].item()), "onnx"
        except Exception:
            pass
    return None, "heuristic"


def evaluate_compliance(
    text: str,
    metadata: Mapping[str, Any] | None = None,
) -> ComplianceClassification:
    """Return compliance probability and rule failures for ``text``."""

    payload = compliance_features(text, metadata)
    features = payload["features"]
    vector = _feature_vector(features)
    probability, source = _run_model(vector)
    if probability is None:
        probability = _heuristic_probability(features)
        source = "heuristic"
    probability = float(max(0.0, min(1.0, probability)))
    failing = _rule_violations(features)
    return ComplianceClassification(
        probability=probability, failing_rules=failing, features=features, source=source
    )


def compliance_model_metadata() -> "ModelMetadata | None":
    """Return metadata describing the compliance critic when available."""

    if _onnx is None:
        return None
    try:
        session = _onnx.get_session(model_path())
        return _onnx.get_model_metadata(session)
    except Exception:
        return None

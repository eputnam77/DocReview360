"""Routing critic utilities implemented with NumPy."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

try:  # pragma: no cover - optional dependency
    import onnx
    from onnx import TensorProto, helper
except ModuleNotFoundError:  # pragma: no cover - minimal installs
    onnx = None  # type: ignore[assignment]
    TensorProto = None  # type: ignore[assignment]
    helper = None  # type: ignore[assignment]

from .features import routing_features

__all__ = [
    "ROUTING_FEATURE_NAMES",
    "RoutingCritic",
    "RoutingExample",
    "export_routing_critic_to_onnx",
    "routing_feature_vector",
    "train_routing_critic",
]


ROUTING_FEATURE_NAMES: tuple[str, ...] = (
    "content_size",
    "novelty",
    "duplication",
    "structure",
    "priority",
    "metadata_signal",
)


def routing_feature_vector(text: str, metadata: Mapping[str, Any] | None = None) -> np.ndarray:
    """Return routing feature vector for ``text`` suitable for model input."""

    payload = routing_features(text, metadata)
    features = payload["features"]
    return np.array([float(features[name]) for name in ROUTING_FEATURE_NAMES], dtype=np.float32)


@dataclass
class RoutingExample:
    """Single labelled example used for routing critic training."""

    text: str
    reviewer: str
    approved: bool
    metadata: Mapping[str, Any] | None = None


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits)
    exp = np.exp(shifted)
    denom = np.sum(exp)
    if denom == 0:
        return np.full_like(exp, 1.0 / len(exp))
    return exp / denom


class RoutingCritic:
    """Simple linear critic producing approval likelihood and reviewer logits."""

    def __init__(self, reviewers: Sequence[str], *, input_dim: int | None = None) -> None:
        if not reviewers:
            raise ValueError("reviewers must be non-empty")
        self.reviewers: tuple[str, ...] = tuple(reviewers)
        self.input_dim = input_dim or len(ROUTING_FEATURE_NAMES)
        self.approval_weights = np.zeros(self.input_dim, dtype=np.float32)
        self.approval_bias = 0.0
        self.reviewer_weights = np.zeros((len(self.reviewers), self.input_dim), dtype=np.float32)
        self.reviewer_bias = np.zeros(len(self.reviewers), dtype=np.float32)

    def predict(self, features: np.ndarray) -> tuple[float, np.ndarray]:
        """Return approval probability and reviewer logits for ``features``."""

        features = features.astype(np.float32)
        approval_logit = float(np.dot(self.approval_weights, features) + self.approval_bias)
        approval_probability = float(_sigmoid(np.array([approval_logit]))[0])
        reviewer_logits = self.reviewer_weights @ features + self.reviewer_bias
        return approval_probability, reviewer_logits.astype(np.float32)


def _one_hot(index: int, size: int) -> np.ndarray:
    vec = np.zeros(size, dtype=np.float32)
    vec[index] = 1.0
    return vec


def train_routing_critic(
    reviewers: Sequence[str],
    examples: Sequence[RoutingExample],
    *,
    epochs: int = 200,
    lr: float = 0.05,
) -> RoutingCritic:
    """Train a :class:`RoutingCritic` using labelled ``examples``."""

    if not reviewers:
        raise ValueError("reviewers must be non-empty")
    if not examples:
        raise ValueError("at least one example required")

    critic = RoutingCritic(reviewers)
    reviewer_to_index = {name: idx for idx, name in enumerate(reviewers)}

    for example in examples:
        if example.reviewer not in reviewer_to_index:
            raise ValueError(f"unknown reviewer '{example.reviewer}'")

    for _ in range(epochs):
        for example in examples:
            features = routing_feature_vector(example.text, example.metadata)
            approval_prob, reviewer_logits = critic.predict(features)

            target = 1.0 if example.approved else 0.0
            error = approval_prob - target
            critic.approval_weights -= lr * error * features
            critic.approval_bias -= lr * error

            reviewer_probs = _softmax(reviewer_logits)
            target_vec = _one_hot(reviewer_to_index[example.reviewer], len(reviewers))
            diff = reviewer_probs - target_vec
            critic.reviewer_weights -= lr * diff[:, None] * features[None, :]
            critic.reviewer_bias -= lr * diff

    return critic


def export_routing_critic_to_onnx(
    critic: RoutingCritic,
    path: str | Path,
    *,
    metadata: Mapping[str, str] | None = None,
) -> Path:
    """Export ``critic`` weights to ONNX format."""

    if helper is None or onnx is None:
        raise RuntimeError("onnx is not installed")

    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    input_tensor = helper.make_tensor_value_info(
        "input", TensorProto.FLOAT, [None, critic.input_dim]
    )
    approval_tensor = helper.make_tensor_value_info("approval", TensorProto.FLOAT, [None, 1])
    logits_tensor = helper.make_tensor_value_info(
        "reviewer_logits", TensorProto.FLOAT, [None, len(critic.reviewers)]
    )

    approval_weights = helper.make_tensor(
        "W_app",
        TensorProto.FLOAT,
        [critic.input_dim, 1],
        critic.approval_weights.astype(np.float32),
    )
    approval_bias = helper.make_tensor(
        "b_app", TensorProto.FLOAT, [1], np.array([critic.approval_bias], dtype=np.float32)
    )
    reviewer_weights = helper.make_tensor(
        "W_rev",
        TensorProto.FLOAT,
        [critic.input_dim, len(critic.reviewers)],
        critic.reviewer_weights.T.astype(np.float32),
    )
    reviewer_bias = helper.make_tensor(
        "b_rev", TensorProto.FLOAT, [len(critic.reviewers)], critic.reviewer_bias.astype(np.float32)
    )

    nodes = [
        helper.make_node("MatMul", ["input", "W_app"], ["approval_matmul"]),
        helper.make_node("Add", ["approval_matmul", "b_app"], ["approval_linear"]),
        helper.make_node("Sigmoid", ["approval_linear"], ["approval"]),
        helper.make_node("MatMul", ["input", "W_rev"], ["reviewer_matmul"]),
        helper.make_node("Add", ["reviewer_matmul", "b_rev"], ["reviewer_logits"]),
    ]

    graph = helper.make_graph(
        nodes,
        "routing_critic",
        [input_tensor],
        [approval_tensor, logits_tensor],
        initializer=[approval_weights, approval_bias, reviewer_weights, reviewer_bias],
    )

    model = helper.make_model(
        graph,
        producer_name="docreview360",
        opset_imports=[helper.make_opsetid("", 13)],
        ir_version=9,
    )
    metadata_map = {
        "docreview360:critic": "routing",
        "docreview360:architecture": "linear-routing",
        "docreview360:reviewers": ",".join(critic.reviewers),
    }
    if metadata:
        metadata_map.update(metadata)
    model.metadata_props.clear()
    for key, value in metadata_map.items():
        entry = model.metadata_props.add()
        entry.key = key
        entry.value = value

    onnx.checker.check_model(model)
    onnx.save_model(model, dest)
    return dest

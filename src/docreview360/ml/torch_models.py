"""Torch-based critic models and ONNX export utilities."""

from __future__ import annotations

import hashlib
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Mapping, MutableMapping, Sequence

try:
    import torch
    from torch import Tensor, nn
except Exception:
    torch = None  # type: ignore[assignment]
    Tensor = None  # type: ignore[assignment]
    nn = None  # type: ignore[assignment]

from .features import FANN_FEATURE_NAMES, quality_features

__all__ = [
    "CriticConfig",
    "TinyCritic",
    "build_clarity_critic",
    "build_compliance_critic",
    "build_impact_critic",
    "build_risk_critic",
    "critic_builders",
    "export_critic_to_onnx",
    "get_default_critics",
    "load_critic",
    "save_critic",
    "train_critic",
    "update_critic",
]


def _legacy_fann_vector(text: str) -> list[float]:
    legacy = quality_features(text)["legacy"]["fann"]
    return [legacy[name] for name in FANN_FEATURE_NAMES]


@dataclass(frozen=True)
class CriticConfig:
    """Configuration describing a tiny MLP critic."""

    name: str
    hidden_dim: int = 16
    dropout: float = 0.0
    input_dim: int = len(FANN_FEATURE_NAMES)


if torch is not None and nn is not None:

    class TinyCritic(nn.Module):
        """Small sigmoid-activated MLP used for heuristic scoring."""

        def __init__(self, config: CriticConfig) -> None:
            super().__init__()
            self.config = config
            layers: list[nn.Module] = [nn.Linear(config.input_dim, config.hidden_dim), nn.Tanh()]
            if config.dropout:
                layers.append(nn.Dropout(p=config.dropout))
            layers.append(nn.Linear(config.hidden_dim, 1))
            self.network = nn.Sequential(*layers)
            self._sigmoid = nn.Sigmoid()
            self.reset_parameters()

        @property
        def name(self) -> str:  # pragma: no cover - trivial alias
            return self.config.name

        @property
        def input_dim(self) -> int:  # pragma: no cover - trivial alias
            return self.config.input_dim

        @property
        def hidden_dim(self) -> int:  # pragma: no cover - trivial alias
            return self.config.hidden_dim

        @property
        def dropout(self) -> float:  # pragma: no cover - trivial alias
            return self.config.dropout

        def reset_parameters(self, strategy: str = "xavier") -> None:
            """Reset weights using ``strategy``."""

            for module in self.network:
                if not isinstance(module, nn.Linear):
                    continue
                if strategy == "zeros":
                    nn.init.zeros_(module.weight)
                    nn.init.zeros_(module.bias)
                elif strategy == "xavier":
                    nn.init.xavier_uniform_(module.weight)
                    nn.init.zeros_(module.bias)
                else:  # pragma: no cover - defensive branch
                    raise ValueError(f"unknown reset strategy: {strategy}")

        def forward(self, inputs: Tensor) -> Tensor:
            logits = self.network(inputs)
            return self._sigmoid(logits)

        def predict(self, text: str, feature_weights: Sequence[float] | None = None) -> float:
            """Return score for ``text`` optionally applying ``feature_weights``."""

            feats = torch.tensor(_legacy_fann_vector(text), dtype=torch.float32)
            if feature_weights is not None:
                weights = torch.tensor(feature_weights, dtype=torch.float32)
                if weights.numel() != feats.numel():
                    raise ValueError("feature_weights must match feature vector length")
                feats = feats * weights
            with torch.no_grad():
                output = self.forward(feats.unsqueeze(0))
            return float(output.squeeze().item())

        def predict_features(self, features: Sequence[Sequence[float]] | Tensor) -> Tensor:
            """Return predictions for a batch of ``features``."""

            if not isinstance(features, Tensor):
                batch = torch.tensor(features, dtype=torch.float32)
            else:
                batch = features.float()
            with torch.no_grad():
                return self.forward(batch)

else:
    import numpy as np

    class TinyCritic:
        """Numpy-backed critic used when torch is unavailable."""

        def __init__(self, config: CriticConfig) -> None:
            self.config = config
            self._rng = np.random.default_rng()
            self._weights: dict[str, np.ndarray] = {}
            self.reset_parameters()

        @property
        def name(self) -> str:
            return self.config.name

        @property
        def input_dim(self) -> int:
            return self.config.input_dim

        @property
        def hidden_dim(self) -> int:
            return self.config.hidden_dim

        @property
        def dropout(self) -> float:
            return self.config.dropout

        def train(self) -> "TinyCritic":
            return self

        def eval(self) -> "TinyCritic":
            return self

        def reset_parameters(self, strategy: str = "xavier") -> None:
            """Reset weights using ``strategy``."""

            if strategy not in {"zeros", "xavier"}:
                raise ValueError(f"unknown reset strategy: {strategy}")
            if strategy == "zeros":
                self._weights = {
                    "w1": np.zeros((self.input_dim, self.hidden_dim), dtype=np.float32),
                    "b1": np.zeros((self.hidden_dim,), dtype=np.float32),
                    "w2": np.zeros((self.hidden_dim, 1), dtype=np.float32),
                    "b2": np.zeros((1,), dtype=np.float32),
                }
                return
            limit1 = np.sqrt(6 / (self.input_dim + self.hidden_dim))
            limit2 = np.sqrt(6 / (self.hidden_dim + 1))
            self._weights = {
                "w1": self._rng.uniform(-limit1, limit1, size=(self.input_dim, self.hidden_dim)).astype(
                    np.float32
                ),
                "b1": np.zeros((self.hidden_dim,), dtype=np.float32),
                "w2": self._rng.uniform(-limit2, limit2, size=(self.hidden_dim, 1)).astype(np.float32),
                "b2": np.zeros((1,), dtype=np.float32),
            }

        def _as_array(self, features: Sequence[Sequence[float]] | np.ndarray) -> np.ndarray:
            return np.asarray(features, dtype=np.float32)

        def forward(self, inputs: Sequence[Sequence[float]] | np.ndarray) -> np.ndarray:
            batch = self._as_array(inputs)
            hidden = np.tanh(batch @ self._weights["w1"] + self._weights["b1"])
            logits = hidden @ self._weights["w2"] + self._weights["b2"]
            return 1.0 / (1.0 + np.exp(-logits))

        def predict(self, text: str, feature_weights: Sequence[float] | None = None) -> float:
            feats = np.array(_legacy_fann_vector(text), dtype=np.float32)
            if feature_weights is not None:
                weights = np.array(feature_weights, dtype=np.float32)
                if weights.size != feats.size:
                    raise ValueError("feature_weights must match feature vector length")
                feats = feats * weights
            output = self.forward(feats.reshape(1, -1))
            return float(output.squeeze().item())

        def predict_features(
            self, features: Sequence[Sequence[float]] | np.ndarray
        ) -> np.ndarray:
            return self.forward(features)

        def state_dict(self) -> dict[str, np.ndarray]:
            return {key: value.copy() for key, value in self._weights.items()}

        def load_state_dict(self, payload: Mapping[str, np.ndarray]) -> None:
            self._weights = {key: np.array(value, dtype=np.float32) for key, value in payload.items()}


def _build_critic(name: str, hidden: int, dropout: float = 0.0) -> TinyCritic:
    return TinyCritic(CriticConfig(name=name, hidden_dim=hidden, dropout=dropout))


def build_clarity_critic() -> TinyCritic:
    """Critic tuned for clarity scoring."""

    return _build_critic("clarity", hidden=12, dropout=0.05)


def build_compliance_critic() -> TinyCritic:
    """Critic tuned for compliance scoring."""

    return _build_critic("compliance", hidden=16, dropout=0.1)


def build_impact_critic() -> TinyCritic:
    """Critic tuned for impact scoring."""

    return _build_critic("impact", hidden=10, dropout=0.0)


def build_risk_critic() -> TinyCritic:
    """Critic tuned for risk detection."""

    return _build_critic("risk", hidden=8, dropout=0.0)


critic_builders: Dict[str, Callable[[], TinyCritic]] = {
    "clarity": build_clarity_critic,
    "compliance": build_compliance_critic,
    "impact": build_impact_critic,
    "risk": build_risk_critic,
}


def get_default_critics() -> Dict[str, TinyCritic]:
    """Instantiate the four default critics."""

    return {name: builder() for name, builder in critic_builders.items()}


def _features_tensor(texts: Sequence[str]) -> Tensor:
    feats = [_legacy_fann_vector(text) for text in texts]
    if torch is None:
        import numpy as np

        return np.asarray(feats, dtype=np.float32)
    return torch.tensor(feats, dtype=torch.float32)


def train_critic(
    critic: TinyCritic,
    texts: Sequence[str],
    labels: Sequence[int],
    *,
    epochs: int = 50,
    lr: float = 0.01,
) -> TinyCritic:
    """Train ``critic`` on ``texts`` and ``labels``."""

    if len(texts) != len(labels):
        raise ValueError("texts and labels must be the same length")
    if not texts:
        raise ValueError("training requires at least one example")

    critic.train()
    features = _features_tensor(texts)
    if torch is None or nn is None:
        import numpy as np

        targets = np.asarray(labels, dtype=np.float32).reshape(-1, 1)
        batch = np.asarray(features, dtype=np.float32)
        for _ in range(epochs):
            outputs = critic.forward(batch)
            error = outputs - targets
            hidden = np.tanh(batch @ critic._weights["w1"] + critic._weights["b1"])
            grad_w2 = hidden.T @ error / len(batch)
            grad_b2 = error.mean(axis=0)
            hidden_grad = error @ critic._weights["w2"].T * (1 - hidden**2)
            grad_w1 = batch.T @ hidden_grad / len(batch)
            grad_b1 = hidden_grad.mean(axis=0)
            critic._weights["w1"] -= lr * grad_w1
            critic._weights["b1"] -= lr * grad_b1
            critic._weights["w2"] -= lr * grad_w2
            critic._weights["b2"] -= lr * grad_b2
    else:
        targets = torch.tensor(labels, dtype=torch.float32).unsqueeze(1)
        criterion = nn.BCELoss()
        optimizer = torch.optim.Adam(critic.parameters(), lr=lr)

        for _ in range(epochs):
            optimizer.zero_grad()
            outputs = critic.forward(features)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()

    critic.eval()
    return critic


def update_critic(
    critic: TinyCritic,
    texts: Sequence[str],
    labels: Sequence[int],
    *,
    epochs: int = 25,
    lr: float = 0.005,
) -> TinyCritic:
    """Fine-tune ``critic`` using additional labelled ``texts``."""

    if not texts:
        return critic
    return train_critic(critic, texts, labels, epochs=epochs, lr=lr)


def save_critic(critic: TinyCritic, path: str | Path) -> Path:
    """Persist ``critic`` weights and configuration to ``path``."""

    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "config": {
            "name": critic.name,
            "hidden_dim": critic.hidden_dim,
            "dropout": critic.dropout,
            "input_dim": critic.input_dim,
        },
        "state_dict": critic.state_dict(),
    }
    if torch is None:
        import pickle

        with open(dest, "wb") as fh:
            pickle.dump(payload, fh)
    else:
        torch.save(payload, dest)
    return dest


def load_critic(path: str | Path) -> TinyCritic:
    """Load a critic previously saved with :func:`save_critic`."""

    if torch is None:
        import pickle

        with open(Path(path), "rb") as fh:
            payload = pickle.load(fh)
    else:
        payload = torch.load(Path(path), map_location="cpu")
    config = CriticConfig(**payload["config"])
    critic = TinyCritic(config)
    critic.load_state_dict(payload["state_dict"])
    critic.eval()
    return critic


def _attach_metadata(model_path: Path, metadata: Mapping[str, str]) -> None:
    import onnx

    model = onnx.load_model(model_path)
    props: MutableMapping[str, str] = {item.key: item.value for item in model.metadata_props}
    props.update(metadata)
    del model.metadata_props[:]
    for key, value in props.items():
        entry = model.metadata_props.add()
        entry.key = key
        entry.value = value
    onnx.save_model(model, model_path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def export_critic_to_onnx(
    critic: TinyCritic,
    path: str | Path,
    *,
    opset: int = 18,
    metadata: Mapping[str, str] | None = None,
    quantize: bool = False,
) -> Dict[str, str]:
    """Export ``critic`` to ONNX format with optional INT8 quantisation."""

    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    critic.eval()

    if torch is None:
        import onnx
        from onnx import helper, numpy_helper

        input_tensor = helper.make_tensor_value_info(
            "input", onnx.TensorProto.FLOAT, ["batch", critic.input_dim]
        )
        output_tensor = helper.make_tensor_value_info("output", onnx.TensorProto.FLOAT, ["batch", 1])
        w1 = numpy_helper.from_array(critic._weights["w1"], name="w1")
        b1 = numpy_helper.from_array(critic._weights["b1"], name="b1")
        w2 = numpy_helper.from_array(critic._weights["w2"], name="w2")
        b2 = numpy_helper.from_array(critic._weights["b2"], name="b2")

        nodes = [
            helper.make_node("MatMul", ["input", "w1"], ["hidden_linear"]),
            helper.make_node("Add", ["hidden_linear", "b1"], ["hidden_bias"]),
            helper.make_node("Tanh", ["hidden_bias"], ["hidden"]),
            helper.make_node("MatMul", ["hidden", "w2"], ["logits_linear"]),
            helper.make_node("Add", ["logits_linear", "b2"], ["logits"]),
            helper.make_node("Sigmoid", ["logits"], ["output"]),
        ]
        graph = helper.make_graph(
            nodes,
            "docreview360_critic",
            [input_tensor],
            [output_tensor],
            initializer=[w1, b1, w2, b2],
        )
        model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", opset)])
        onnx.save_model(model, path_obj)
    else:
        dummy_input = torch.zeros(1, critic.input_dim, dtype=torch.float32)
        torch.onnx.export(
            critic,
            dummy_input,
            path_obj,
            input_names=["input"],
            output_names=["output"],
            dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}},
            opset_version=opset,
        )

    meta: Dict[str, str] = {
        "docreview360:critic": critic.name,
        "docreview360:architecture": "tiny-mlp",
        "docreview360:quantized": "true" if quantize else "false",
    }
    if metadata:
        meta.update(metadata)
    _attach_metadata(path_obj, meta)

    if quantize:
        from tempfile import NamedTemporaryFile

        try:
            from onnxruntime.quantization import QuantType, quantize_dynamic
        except ModuleNotFoundError:
            warnings.warn(
                "onnxruntime.quantization is unavailable; skipping INT8 quantization.",
                RuntimeWarning,
            )
            return {"path": str(path_obj), "sha256": _sha256(path_obj), **meta}

        with NamedTemporaryFile(suffix=".onnx", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            quantize_dynamic(
                model_input=str(path_obj),
                model_output=str(tmp_path),
                weight_type=QuantType.QInt8,
            )
            tmp_path.replace(path_obj)
            _attach_metadata(path_obj, meta)
        finally:
            tmp_path.unlink(missing_ok=True)

    return {"path": str(path_obj), "sha256": _sha256(path_obj), **meta}

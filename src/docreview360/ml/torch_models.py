"""Torch-based critic models and ONNX export utilities."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Mapping, MutableMapping, Sequence

import torch
from torch import Tensor, nn

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
    torch.save(payload, dest)
    return dest


def load_critic(path: str | Path) -> TinyCritic:
    """Load a critic previously saved with :func:`save_critic`."""

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
    model.metadata_props.clear()
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

        from onnxruntime.quantization import QuantType, quantize_dynamic

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

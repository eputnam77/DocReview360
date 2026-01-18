"""ONNX-exported anomaly detector for signature verification telemetry."""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

try:  # pragma: no cover - optional dependency
    import torch
    import torch.nn as nn
except Exception:  # pragma: no cover - torch not available in minimal environments
    torch = None  # type: ignore[assignment]
    nn = None  # type: ignore[assignment]

from onnx import TensorProto, helper

from .features import SIGNATURE_ANOMALY_FEATURE_NAMES
from .onnx_infer import ModelMetadata, get_model_metadata, get_session, infer

MODEL_VERSION = "1.0.0"
MODEL_NAME = "signature_anomaly.onnx"
MODEL_PATH = Path(__file__).with_name("assets") / MODEL_NAME

_ANOMALY_WEIGHTS = (-1.0, -2.0, 1.5, 2.0, -1.5, -2.5, -0.8, -1.0)
_ANOMALY_BIAS = 1.8


if nn is not None:  # pragma: no cover - executed only when torch is available

    class _SignatureAnomalyNet(nn.Module):
        """Single-layer logistic regression calibrated for heuristic telemetry."""

        def __init__(self) -> None:
            super().__init__()
            input_dim = len(SIGNATURE_ANOMALY_FEATURE_NAMES)
            self.linear = nn.Linear(input_dim, 1)
            self.activation = nn.Sigmoid()
            self._initialise_weights()

        def _initialise_weights(self) -> None:
            weights = torch.tensor(_ANOMALY_WEIGHTS, dtype=torch.float32)
            bias = torch.tensor([_ANOMALY_BIAS], dtype=torch.float32)
            with torch.no_grad():
                self.linear.weight.copy_(weights.unsqueeze(0))
                self.linear.bias.copy_(bias)

        def forward(self, inputs: torch.Tensor) -> torch.Tensor:
            logits = self.linear(inputs.float())
            return self.activation(logits)

else:  # pragma: no cover - executed in environments without torch

    _SignatureAnomalyNet = None  # type: ignore[assignment]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _attach_metadata(path: Path, metadata: Mapping[str, str]) -> None:
    import onnx

    model = onnx.load_model(path)
    props = {item.key: item.value for item in model.metadata_props}
    props.update(metadata)
    model.metadata_props.clear()
    for key, value in props.items():
        entry = model.metadata_props.add()
        entry.key = key
        entry.value = value
    onnx.save_model(model, path)


def _export_with_torch(path_obj: Path, opset: int) -> None:
    if torch is None or nn is None or _SignatureAnomalyNet is None:
        raise RuntimeError("torch not available")
    model = _SignatureAnomalyNet()
    model.eval()
    dummy = torch.zeros(1, len(SIGNATURE_ANOMALY_FEATURE_NAMES), dtype=torch.float32)
    torch.onnx.export(
        model,
        dummy,
        path_obj,
        input_names=["input"],
        output_names=["score"],
        dynamic_axes={"input": {0: "batch"}, "score": {0: "batch"}},
        opset_version=opset,
    )


def _export_with_onnx(path_obj: Path, opset: int) -> None:
    import onnx

    feature_dim = len(SIGNATURE_ANOMALY_FEATURE_NAMES)
    input_tensor = helper.make_tensor_value_info("input", TensorProto.FLOAT, ["batch", feature_dim])
    output_tensor = helper.make_tensor_value_info("score", TensorProto.FLOAT, ["batch", 1])
    weight_tensor = helper.make_tensor(
        "weights",
        TensorProto.FLOAT,
        [feature_dim, 1],
        _ANOMALY_WEIGHTS,
    )
    bias_tensor = helper.make_tensor(
        "bias",
        TensorProto.FLOAT,
        [1],
        [_ANOMALY_BIAS],
    )
    matmul = helper.make_node("MatMul", ["input", "weights"], ["matmul_out"])
    add = helper.make_node("Add", ["matmul_out", "bias"], ["logits"])
    sigmoid = helper.make_node("Sigmoid", ["logits"], ["score"])
    graph = helper.make_graph(
        [matmul, add, sigmoid],
        "signature_anomaly",
        [input_tensor],
        [output_tensor],
        initializer=[weight_tensor, bias_tensor],
    )
    model = helper.make_model(
        graph,
        producer_name="docreview360",
        opset_imports=[helper.make_opsetid("", opset)],
    )
    onnx.save_model(model, path_obj)


def export_signature_anomaly_model(
    path: str | Path = MODEL_PATH,
    *,
    opset: int = 18,
) -> dict[str, str]:
    """Export the calibrated PyTorch anomaly model to ONNX."""

    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    if torch is not None and nn is not None and _SignatureAnomalyNet is not None:
        try:
            _export_with_torch(path_obj, opset)
        except Exception:
            _export_with_onnx(path_obj, opset)
    else:
        _export_with_onnx(path_obj, opset)

    metadata = {
        "docreview360:model": "signature-anomaly",
        "docreview360:version": MODEL_VERSION,
    }
    _attach_metadata(path_obj, metadata)
    return {"path": str(path_obj), "sha256": _sha256(path_obj), **metadata}


def _ensure_model(path: str | Path | None = None) -> Path:
    model_path = Path(path) if path else MODEL_PATH
    if not model_path.exists():
        export_signature_anomaly_model(model_path)
    return model_path


def score_signature_anomaly(features: Sequence[float]) -> tuple[float, ModelMetadata]:
    """Return anomaly score and model metadata for ``features``."""

    model_path = _ensure_model()
    array = np.asarray([list(features)], dtype=np.float32)
    try:
        session = get_session(model_path)
        outputs = infer(session, {"input": array})
        score = float(np.clip(outputs[0].squeeze().item(), 0.0, 1.0))
        meta = get_model_metadata(session)
    except Exception:
        linear = float(_ANOMALY_BIAS)
        for weight, value in zip(_ANOMALY_WEIGHTS, array.squeeze(0)):
            linear += float(weight) * float(value)
        score = float(1.0 / (1.0 + math.exp(-linear)))
        score = float(np.clip(score, 0.0, 1.0))
        meta = ModelMetadata(
            path=model_path,
            sha256=_sha256(model_path),
            version=MODEL_VERSION,
            custom_metadata={},
        )
    return score, meta


def get_signature_anomaly_metadata() -> ModelMetadata:
    """Return cached metadata for the signature anomaly detector."""

    model_path = _ensure_model()
    return get_model_metadata(model_path)


__all__ = [
    "MODEL_NAME",
    "MODEL_PATH",
    "MODEL_VERSION",
    "export_signature_anomaly_model",
    "get_signature_anomaly_metadata",
    "score_signature_anomaly",
]

"""Training and evaluation helpers for DocReview360 ML artefacts."""

from __future__ import annotations

import csv
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, MutableMapping, Sequence

import numpy as np

from .onnx_infer import ModelMetadata, get_model_metadata, get_session
from .torch_models import (
    TinyCritic,
    build_clarity_critic,
    critic_builders,
    export_critic_to_onnx,
    load_critic,
    save_critic,
    train_critic,
    update_critic,
)

__all__ = [
    "BenchmarkResult",
    "ModelSummary",
    "TrainingResult",
    "ValidationReport",
    "benchmark_onnx_cpu",
    "format_model_summary",
    "format_validation_report",
    "read_labelled_corpus",
    "summarize_model",
    "train_critic_from_corpus",
    "train_critic_from_csv",
]


@dataclass(frozen=True)
class ValidationReport:
    """Validation accuracy summary for a trained critic."""

    accuracy: float
    correct: int
    total: int


@dataclass(frozen=True)
class TrainingResult:
    """Artefacts generated during critic training and export."""

    critic: TinyCritic
    weights_path: Path
    onnx_path: Path
    onnx_sha256: str
    metadata: Mapping[str, str]
    validation: ValidationReport | None = None


@dataclass(frozen=True)
class BenchmarkResult:
    """Latency measurements gathered from ONNX Runtime inference."""

    average_ms: float
    min_ms: float
    max_ms: float
    runs: int
    batch_size: int


@dataclass(frozen=True)
class ModelSummary:
    """Summary of model metadata for display in CLI validation output."""

    metadata: ModelMetadata


def read_labelled_corpus(path: str | Path) -> tuple[list[str], list[int]]:
    """Return ``texts`` and ``labels`` extracted from ``path``.

    The CSV file must contain ``text`` and ``label`` headers. Labels are coerced
    to integers while texts are returned as-is. Empty files are allowed, in
    which case two empty lists are returned.
    """

    location = Path(path)
    texts: list[str] = []
    labels: list[int] = []
    with location.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None or {"text", "label"} - set(reader.fieldnames):
            raise ValueError("CSV corpus must provide 'text' and 'label' columns")
        for row in reader:
            texts.append(row["text"])
            labels.append(int(row["label"]))
    return texts, labels


def _build_critic(name: str) -> TinyCritic:
    if name == "clarity":
        return build_clarity_critic()
    try:
        builder = critic_builders[name]
    except KeyError as exc:  # pragma: no cover - defensive
        raise ValueError(f"unknown critic '{name}'") from exc
    return builder()


def train_critic_from_corpus(
    texts: Sequence[str],
    labels: Sequence[int],
    *,
    critic_name: str = "clarity",
    update_path: str | Path | None = None,
    epochs: int | None = None,
    lr: float | None = None,
) -> TinyCritic:
    """Train or update a critic using in-memory ``texts`` and ``labels``."""

    if update_path:
        critic = load_critic(update_path)
        critic = update_critic(
            critic,
            texts,
            labels,
            epochs=epochs or 25,
            lr=lr or 0.005,
        )
    else:
        critic = _build_critic(critic_name)
        critic = train_critic(
            critic,
            texts,
            labels,
            epochs=epochs or 50,
            lr=lr or 0.01,
        )
    return critic


def train_critic_from_csv(
    corpus_path: str | Path,
    output_base: str | Path,
    *,
    critic_name: str = "clarity",
    update_path: str | Path | None = None,
    quantize: bool = False,
    metadata: Mapping[str, str] | None = None,
    validation_path: str | Path | None = None,
) -> TrainingResult:
    """Train a critic using a CSV corpus and export artefacts to disk."""

    texts, labels = read_labelled_corpus(corpus_path)
    critic = train_critic_from_corpus(
        texts,
        labels,
        critic_name=critic_name,
        update_path=update_path,
    )

    base = Path(output_base)
    weights_path = save_critic(critic, base.with_suffix(".pt"))

    meta: MutableMapping[str, str] = {
        "docreview360:source": "cli.ml.train",
        "docreview360:critic": critic.name,
    }
    if metadata:
        meta.update({str(k): str(v) for k, v in metadata.items()})

    export_info = export_critic_to_onnx(
        critic,
        base.with_suffix(".onnx"),
        metadata=meta,
        quantize=quantize,
    )

    validation: ValidationReport | None = None
    if validation_path is not None:
        v_texts, v_labels = read_labelled_corpus(validation_path)
        if not v_labels:
            raise ValueError("validation corpus is empty")
        predictions = [int(critic.predict(text) >= 0.5) for text in v_texts]
        correct = sum(int(pred == label) for pred, label in zip(predictions, v_labels))
        accuracy = correct / len(v_labels)
        validation = ValidationReport(accuracy=accuracy, correct=correct, total=len(v_labels))

    metadata_copy = {
        key: value for key, value in export_info.items() if key not in {"path", "sha256"}
    }

    return TrainingResult(
        critic=critic,
        weights_path=weights_path,
        onnx_path=Path(export_info["path"]),
        onnx_sha256=export_info["sha256"],
        metadata=metadata_copy,
        validation=validation,
    )


def benchmark_onnx_cpu(
    model_path: str | Path,
    *,
    runs: int = 10,
    batch_size: int = 32,
) -> BenchmarkResult:
    """Execute quick CPU-only benchmarks for ``model_path`` using ONNX Runtime."""

    if runs <= 0:
        raise ValueError("runs must be greater than zero")
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero")

    session = get_session(model_path, providers=("CPUExecutionProvider",))
    input_tensor = session.get_inputs()[0]
    shape: list[int] = []
    for index, dim in enumerate(input_tensor.shape):
        if isinstance(dim, str) or dim is None:
            shape.append(batch_size if index == 0 else 1)
        else:
            shape.append(int(dim))

    rng = np.random.default_rng(seed=2024)
    data = rng.random(shape, dtype=np.float32)
    inputs = {input_tensor.name: data}

    # Warm-up run to trigger any lazy initialisation costs.
    session.run(None, inputs)

    timings: list[float] = []
    for _ in range(runs):
        start = time.perf_counter()
        session.run(None, inputs)
        elapsed_ms = (time.perf_counter() - start) * 1000
        timings.append(elapsed_ms)

    return BenchmarkResult(
        average_ms=statistics.fmean(timings),
        min_ms=min(timings),
        max_ms=max(timings),
        runs=runs,
        batch_size=batch_size,
    )


def summarize_model(path: str | Path) -> ModelSummary:
    """Collect model metadata for ``path``."""

    metadata = get_model_metadata(path)
    return ModelSummary(metadata=metadata)


def format_model_summary(summary: ModelSummary) -> str:
    """Return a human-readable representation of ``summary``."""

    lines = [f"Model: {summary.metadata.path}"]
    lines.append(f"  sha256: {summary.metadata.sha256}")
    if summary.metadata.version:
        lines.append(f"  version: {summary.metadata.version}")
    if summary.metadata.custom_metadata:
        lines.append("  metadata:")
        for key in sorted(summary.metadata.custom_metadata):
            value = summary.metadata.custom_metadata[key]
            lines.append(f"    {key}: {value}")
    return "\n".join(lines)


def format_validation_report(report: ValidationReport) -> str:
    """Format ``report`` for display in CLI output."""

    return f"Validation accuracy: {report.accuracy:.2%} " f"({report.correct}/{report.total})"

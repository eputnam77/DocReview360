#!/usr/bin/env python3
"""CLI utility for training or updating the torch-based critic model."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from docreview360.ml.torch_models import (
    build_clarity_critic,
    export_critic_to_onnx,
    load_critic,
    save_critic,
    train_critic,
    update_critic,
)


def read_corpus(path: str | Path) -> tuple[list[str], list[int]]:
    """Return texts and labels from a ``text,label`` CSV file."""
    texts: list[str] = []
    labels: list[int] = []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            texts.append(row["text"])
            labels.append(int(row["label"]))
    return texts, labels


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the DocReview360 critic model")
    parser.add_argument("corpus", help="CSV corpus with text and label columns")
    parser.add_argument(
        "output",
        help="Base path for saved artefacts (writes .pt and .onnx files)",
    )
    parser.add_argument(
        "--update",
        metavar="PATH",
        help="Existing .pt weights to update instead of training from scratch",
    )
    parser.add_argument(
        "--validation",
        metavar="PATH",
        help="CSV corpus to evaluate validation accuracy",
    )
    parser.add_argument(
        "--min-accuracy",
        type=float,
        default=0.0,
        help="Minimum validation accuracy required (0-1)",
    )
    parser.add_argument(
        "--quantize",
        action="store_true",
        help="Export an additional INT8-quantised ONNX artefact",
    )
    args = parser.parse_args()

    texts, labels = read_corpus(args.corpus)

    if args.update:
        critic = load_critic(args.update)
        critic = update_critic(critic, texts, labels)
    else:
        critic = build_clarity_critic()
        critic = train_critic(critic, texts, labels)

    base_path = Path(args.output)
    weights_path = save_critic(critic, base_path.with_suffix(".pt"))
    export_critic_to_onnx(
        critic,
        base_path.with_suffix(".onnx"),
        metadata={"docreview360:source": "train_fann"},
        quantize=args.quantize,
    )

    print(f"Saved torch weights to {weights_path}")

    if args.validation:
        v_texts, v_labels = read_corpus(args.validation)
        if not v_labels:
            raise SystemExit("validation corpus is empty")
        preds = [int(critic.predict(t) >= 0.5) for t in v_texts]
        correct = sum(int(p == y) for p, y in zip(preds, v_labels))
        accuracy = correct / len(v_labels)
        print(
            f"Validation accuracy: {accuracy:.2%} ({correct}/{len(v_labels)})"
        )
        if accuracy < args.min_accuracy:
            raise SystemExit(1)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()

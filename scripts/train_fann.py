#!/usr/bin/env python3
"""CLI utility for training or updating the faux FANN model."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from docreview360.fann_model import load_weights, save_weights, train_model, update_model


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
    parser = argparse.ArgumentParser(description="Train the faux FANN model")
    parser.add_argument("corpus", help="CSV corpus with text and label columns")
    parser.add_argument("output", help="Destination JSON weights file")
    parser.add_argument(
        "--update",
        metavar="PATH",
        help="Existing weights to update instead of training from scratch",
    )
    args = parser.parse_args()

    texts, labels = read_corpus(args.corpus)

    if args.update:
        weights = load_weights(args.update)
        weights = update_model(weights, texts, labels)
    else:
        weights = train_model(texts, labels)

    save_weights(weights, args.output)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()

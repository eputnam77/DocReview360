# SPDX-License-Identifier: MIT
"""Corpus curation utilities for the ruv-FANN model (Task 106)."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Tuple

from .ai_utils import detect_anomalies


def curate_corpus(texts: Iterable[str], threshold: float = 0.7) -> Tuple[list[str], list[str]]:
    """Split ``texts`` into clean and anomalous lists using ``detect_anomalies``."""
    clean: list[str] = []
    anomalies: list[str] = []
    for text in texts:
        if detect_anomalies(text, threshold):
            anomalies.append(text)
        else:
            clean.append(text)
    return clean, anomalies


def export_corpus(clean: Iterable[str], anomalies: Iterable[str], path: str | Path) -> Path:
    """Write the corpus to ``path`` as CSV with ``label`` column."""
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["text", "label"])  # label 0 clean, 1 anomaly
        for text in clean:
            writer.writerow([text, 0])
        for text in anomalies:
            writer.writerow([text, 1])
    return dest

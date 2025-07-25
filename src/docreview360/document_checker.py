"""Validate documents using JSON rules."""

from __future__ import annotations

# mypy: ignore-errors
import json
from pathlib import Path
from typing import Any, cast

try:
    # GovDocVerify installs as the lowercase ``govdocverify`` package
    # regardless of repository casing. Importing with the original
    # mixed‑case name fails on Linux filesystems.
    from govdocverify.cli import process_document as _gov_run  # type: ignore[import-untyped]
except Exception:  # pragma: no cover - optional dep
    _gov_run = None

import re


def _fallback(file_path: str | Path) -> dict[str, object]:
    """Minimal checker used when GovDocVerify is unavailable."""

    path = Path(file_path)
    text = path.read_text(encoding="utf-8")

    grammar = []
    words = re.split(r"\s+", text)
    for i in range(len(words) - 1):
        if words[i] == words[i + 1]:
            grammar.append(f"repeated word '{words[i]}'")

    accessibility = []
    img_tag = re.compile(r"<img [^>]*>", re.I)
    alt_attr = re.compile(r"alt=\"[^\"]*\"", re.I)
    button_tag = re.compile(r"<button([^>]*)>(.*?)</button>", re.I | re.S)
    aria_label = re.compile(r"aria-label=\"[^\"]*\"", re.I)

    for match in img_tag.finditer(text):
        if not alt_attr.search(match.group(0)):
            accessibility.append("image missing alt text")

    for match in button_tag.finditer(text):
        attrs = match.group(1)
        body = match.group(2)
        if not aria_label.search(attrs) and body.strip() == "":
            accessibility.append("button missing label")

    style_ok = not _detect_anomalies(text)

    return {"grammar": grammar, "accessibility": accessibility, "styleOk": style_ok}


def _detect_anomalies(text: str, threshold: float = 0.7) -> bool:
    words = re.split(r"\s+", text.lower())
    repeated = sum(1 for i in range(len(words) - 1) if words[i] == words[i + 1])
    unique_ratio = len(set(text)) / max(len(text), 1)
    features = [len(text) / 1000, unique_ratio, repeated]
    weights = [0.0, -0.1, 1.2]
    linear = sum(w * f for w, f in zip(weights, features))
    score = 1 / (1 + pow(2.718281828, -linear))
    return score >= threshold


def run_checks(file_path: str | Path) -> dict[str, Any]:
    """Run document checks using GovDocVerify if available."""

    if _gov_run is not None:
        try:
            # GovDocVerify requires a document type argument.  We use "Other"
            # which maps to ``DocumentType.OTHER`` within the library.
            result = _gov_run(str(file_path), "Other")
            return cast(dict[str, Any], result)
        except Exception:
            # Fall back to the lightweight checker if GovDocVerify fails at
            # runtime (e.g. missing config files).
            pass

    return _fallback(str(file_path))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run document checks")
    parser.add_argument("file", help="path to document")
    args = parser.parse_args()

    result = run_checks(args.file)
    print(json.dumps(result))

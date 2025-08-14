"""Validate documents using JSON rules."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, cast

try:
    # GovDocVerify installs as the lowercase ``govdocverify`` package
    # regardless of repository casing. Importing with the original
    # mixed‑case name fails on Linux filesystems.
    from govdocverify.cli import process_document as _gov_run  # type: ignore[import-not-found]
except Exception:
    _gov_run = None

import re

from .ai_utils import _count_syllables

_REQUIRED_SECTIONS = ["introduction", "body", "conclusion"]


def _readability_metrics(text: str) -> Dict[str, float]:
    """Return simple readability scores for ``text``.

    Implements Flesch Reading Ease and Flesch–Kincaid grade level using a
    lightweight syllable estimator. Scores are rounded for stability.
    """

    sentences = max(1, sum(text.count(ch) for ch in ".!?"))
    words = re.findall(r"\b\w+\b", text)
    word_count = len(words) or 1
    syllables = sum(_count_syllables(w) for w in words) or 1
    words_per_sentence = word_count / sentences
    syllables_per_word = syllables / word_count
    flesch = 206.835 - 1.015 * words_per_sentence - 84.6 * syllables_per_word
    grade = 0.39 * words_per_sentence + 11.8 * syllables_per_word - 15.59
    return {
        "flesch_reading_ease": round(flesch, 2),
        "flesch_kincaid_grade": round(grade, 2),
    }


def _style_issues(text: str) -> List[str]:
    """Return a list of simple style-guide issues detected in ``text``."""

    issues: List[str] = []
    if re.search(r"\s{2,}", text):
        issues.append("double spaces detected")
    if "utilize" in text.lower():
        issues.append("avoid 'utilize'; prefer 'use'")
    return issues


def _analyze_structure(
    text: str,
    *,
    required_sections: List[str] | None = None,
    max_words: int = 200,
) -> Dict[str, List[str]]:
    """Inspect document structure for missing or overlong sections.

    Sections are identified using markdown-style headings beginning with ``#``.
    ``required_sections`` are matched case-insensitively.
    """

    required_sections = [s.lower() for s in (required_sections or _REQUIRED_SECTIONS)]
    header = re.compile(r"^\s*#+\s*(.+)")
    sections: Dict[str, List[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        m = header.match(line)
        if m:
            current = m.group(1).strip().lower()
            sections[current] = []
        elif current is not None:
            sections[current].append(line)

    missing = [s for s in required_sections if s not in sections]
    overlong = [
        name for name, lines in sections.items() if len(" ".join(lines).split()) > max_words
    ]
    return {"missing_sections": missing, "overlong_sections": overlong}


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

    style_issues = _style_issues(text)
    style_ok = not _detect_anomalies(text) and not style_issues

    readability = _readability_metrics(text)
    structure = _analyze_structure(text)

    return {
        "grammar": grammar,
        "accessibility": accessibility,
        "styleOk": style_ok,
        "styleIssues": style_issues,
        "readability": readability,
        "structure": structure,
    }


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

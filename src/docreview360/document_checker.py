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
from .ml.compliance_classifier import evaluate_compliance
from .ml.features import quality_features

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
            current = cast(str, m.group(1).strip().lower())
            sections.setdefault(current, [])
        elif current is not None:
            sections[current].append(line)

    missing = [s for s in required_sections if s not in sections]
    overlong = [
        name for name, lines in sections.items() if len(" ".join(lines).split()) > max_words
    ]
    return {"missing_sections": missing, "overlong_sections": overlong}


def _compliance_summary(text: str) -> dict[str, object]:
    classification = evaluate_compliance(text)
    return {
        "probability": classification.probability,
        "failingRules": classification.failing_rules,
        "features": dict(classification.features),
        "source": classification.source,
    }


def _fallback(file_path: str | Path, *, text: str | None = None) -> dict[str, object]:
    """Minimal checker used when GovDocVerify is unavailable."""

    path = Path(file_path)
    if text is None:
        text = path.read_text(encoding="utf-8")

    grammar = []
    # ``re.split`` on whitespace leaves punctuation attached to tokens which
    # meant sequences like "word, word" were missed by the repeated word
    # detector. Extract plain word tokens instead so adjacent words separated
    # only by punctuation are also compared.
    words = re.findall(r"[A-Za-z0-9']+", text)
    for i in range(len(words) - 1):
        if words[i].lower() == words[i + 1].lower():
            grammar.append(f"repeated word '{words[i]}'")

    accessibility = []
    img_tag = re.compile(r"<img\b[^>]*>", re.I)
    # Accept attributes with optional whitespace around the equals sign and
    # support single, double quoted or unquoted ``alt`` values. Capture the
    # value so we can ensure it isn't empty or pure whitespace which would not
    # help assistive technology.  This mirrors the stricter validation performed
    # by the service implementation.
    alt_attr = re.compile(
        r"alt\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>/\'\"]+))(?=[\s>/])",
        re.I,
    )
    button_tag = re.compile(r"<button([^>]*)>(.*?)</button>", re.I | re.S)
    # ``aria-label`` attributes may also include surrounding whitespace. Allow
    # both quoting styles while normalizing incidental spaces.
    aria_label = re.compile(
        r"aria-label\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>/\'\"]+))",
        re.I,
    )

    for match in img_tag.finditer(text):
        m = alt_attr.search(match.group(0))
        value = (m.group(1) or m.group(2) or m.group(3) or "").strip() if m else ""
        if not value:
            accessibility.append("image missing alt text")

    for match in button_tag.finditer(text):
        attrs = match.group(1)
        body = match.group(2)
        # Remove nested tags when checking for visible text. Without this,
        # buttons containing only empty markup like ``<span></span>`` were not
        # flagged as missing labels.
        text_only = re.sub(r"<[^>]+>", "", body).strip()
        m = aria_label.search(attrs)
        label = (m.group(1) or m.group(2) or m.group(3) or "").strip() if m else ""
        if (not label) and text_only == "":
            accessibility.append("button missing label")

    quality = quality_features(text)["features"]
    style_issues = _style_issues(text)
    style_ok = (
        not _detect_anomalies(text)
        and not style_issues
        and quality.get("style", 0.0) >= 0.7
        and quality.get("structure", 0.0) >= 0.5
        and quality.get("duplicate_ratio", 0.0) <= 0.5
    )

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
    # ``re.split`` left punctuation attached to tokens so sequences like
    # ``"bad, bad"`` were treated as different words and missed by the
    # repetition counter.  Extract plain word tokens instead so punctuation
    # does not shield repeated words from detection.
    words = re.findall(r"[A-Za-z0-9']+", text.lower())
    repeated = sum(1 for i in range(len(words) - 1) if words[i] == words[i + 1])
    # ``unique_ratio`` must be computed from tokenised words.  Using raw
    # characters (``set(text)``) overstates anomalies for inputs like
    # ``"aaaaaa"`` which contain a single repeated word but many repeated
    # characters, skewing the score above the threshold.
    unique_ratio = len(set(words)) / max(len(words), 1)
    features = [len(text) / 1000, unique_ratio, repeated]
    weights = [0.0, -0.1, 1.2]
    linear = sum(w * f for w, f in zip(weights, features))
    score = 1 / (1 + pow(2.718281828, -linear))
    return score >= threshold


def run_checks(file_path: str | Path) -> dict[str, Any]:
    """Run document checks using GovDocVerify if available."""

    path = Path(file_path)
    text = path.read_text(encoding="utf-8")
    compliance = _compliance_summary(text)
    if _gov_run is not None:
        try:
            # GovDocVerify requires a document type argument.  We use "Other"
            # which maps to ``DocumentType.OTHER`` within the library.
            result = _gov_run(str(file_path), "Other")
            payload = cast(dict[str, Any], result)
            payload = dict(payload)
            payload["compliance"] = compliance
            return payload
        except Exception:
            # Fall back to the lightweight checker if GovDocVerify fails at
            # runtime (e.g. missing config files).
            pass

    fallback = _fallback(str(file_path), text=text)
    fallback["compliance"] = compliance
    return fallback


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run document checks")
    parser.add_argument("file", help="path to document")
    args = parser.parse_args()

    result = run_checks(args.file)
    print(json.dumps(result))

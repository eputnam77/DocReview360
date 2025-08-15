"""Utility helpers simulating AI integrations for scoring, validation, and workflow routing.

This module contains:
- Prompt and feedback template management.
- Lightweight SynthLang text compression simulation.
- Faux FANN-style scoring for style, structure, and readability.
- Heuristic and GovDocVerify-based style checks.
- Workflow-friendly helpers for anomaly detection, document type suggestions, and export format hints.

Dependencies:
- GovDocVerify (optional). Falls back to internal heuristics when unavailable.
"""

from __future__ import annotations

import math
import os
import re
import tempfile
from typing import TYPE_CHECKING, Dict, Any, Callable, Optional

if TYPE_CHECKING:
    from .documents import DocumentModel

# ---------------------------------------------------------------------------
# Configurable constants & defaults
# ---------------------------------------------------------------------------

# Feature names for FANN-like scoring
FANN_FEATURE_NAMES = [
    "length",
    "unique_ratio",
    "repeated",
    "readability",
    "style",
    "structure",
]

# Default stop words for SynthLang compression
SYNTH_STOP_WORDS = {
    "the", "and", "is", "a", "an", "of", "in", "to",
}

# FANN weights (configurable)
_FANN_WEIGHTS = [0.0, -0.1, 1.2, -0.1, -0.2, -0.2]

# Style-scoring max sentence length
_MAX_SENT_LEN = 120

# Default anomaly detection threshold
DEFAULT_ANOMALY_THRESHOLD = 0.7

# Feedback and prompt templates
FEEDBACK_TEMPLATES: Dict[str, str] = {"default": "Feedback: {text}"}
PROMPT_TEMPLATES: Dict[str, str] = {"default": "{text}"}

# SynthLang enable flag
synth_enabled = False

# Hook for custom heuristic rules (callables that take str -> bool)
CUSTOM_STYLE_RULES: list[Callable[[str], bool]] = []

# ---------------------------------------------------------------------------
# Template management
# ---------------------------------------------------------------------------

def apply_feedback_template(template: str, text: str) -> str:
    """Insert `text` into the feedback template."""
    return template.replace("{text}", text)


def add_feedback_template(name: str, template: str) -> None:
    """Register a new feedback template."""
    if "{text}" not in template:
        raise ValueError("Feedback template must contain '{text}' placeholder.")
    FEEDBACK_TEMPLATES[name] = template


def add_prompt_template(name: str, template: str) -> None:
    """Register a new prompt template for the Prompt-Engine."""
    if "{text}" not in template and not re.search(r"\{[a-zA-Z_]+\}", template):
        raise ValueError("Prompt template must contain at least one placeholder.")
    PROMPT_TEMPLATES[name] = template


def render_prompt(name: str, **context: str) -> str:
    """Return a prompt rendered with the given `context`."""
    tmpl = PROMPT_TEMPLATES.get(name, PROMPT_TEMPLATES["default"])
    try:
        return tmpl.format(**context)
    except KeyError as e:
        raise ValueError(f"Missing placeholder in prompt context: {e}") from e


def generate_feedback(name: str, text: str) -> str:
    """Return formatted feedback using the named template."""
    tmpl = FEEDBACK_TEMPLATES.get(name, FEEDBACK_TEMPLATES["default"])
    return apply_feedback_template(tmpl, text)

# ---------------------------------------------------------------------------
# SynthLang compression simulation
# ---------------------------------------------------------------------------

def synth_compress(text: str) -> str:
    """Reduce token count by removing stop words and vowels when enabled."""
    if not synth_enabled:
        return text
    words = [w for w in text.split() if w.lower() not in SYNTH_STOP_WORDS]
    no_vowels = "".join(ch for ch in " ".join(words) if ch.lower() not in "aeiou")
    return no_vowels

# ---------------------------------------------------------------------------
# Style and structure scoring
# ---------------------------------------------------------------------------

try:  # pragma: no cover
    from govdocverify.cli import process_document as _gov_run  # type: ignore[import-not-found]
except Exception:
    _gov_run = None


def _count_syllables(word: str) -> int:
    """Rough syllable estimator used for readability features."""
    groups = re.findall(r"[aeiouy]+", word.lower())
    return max(1, len(groups))


def _heuristic_style_score(text: str) -> float:
    """Return the fraction of sentences meeting simple style rules."""
    sentences_raw = re.findall(r".*?[.!?](?:\s|$)", text, re.S) or [text]

    good = 0
    for raw in sentences_raw:
        if not raw.strip():
            continue
        lines = raw.splitlines()
        trailing_ws = any(re.search(r"[ \t]+$", line) for line in lines)
        s = raw.strip()
        words = s.split()
        has_repeat = any(w1.lower() == w2.lower() for w1, w2 in zip(words, words[1:]))
        missing_space = re.search(r"[;,](?!\s)", s)
        repeated_caps = re.search(r"[A-Z]{2,}[a-z]", s)

        # Base rules
        passes_base = (
            s[0].isupper()
            and s[-1] in ".!?"
            and not re.search(r"\s{2,}", s)
            and not re.search(r"[.!?]{2,}", s)
            and not has_repeat
            and not missing_space
            and not trailing_ws
            and not repeated_caps
            and len(s) <= _MAX_SENT_LEN
        )

        # Custom rules
        passes_custom = all(rule(s) for rule in CUSTOM_STYLE_RULES)

        if passes_base and passes_custom:
            good += 1

    return good / len(sentences_raw)


def style_guide_score(text: str) -> float:
    """Return a style score using GovDocVerify when available; fall back otherwise."""
    if _gov_run is not None:
        try:
            with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as tmp:
                tmp.write(text)
                tmp.flush()
                path = tmp.name
            try:
                result = _gov_run(path, "Other")
            finally:
                os.unlink(path)
            issues = result.get("styleIssues", [])  # type: ignore[assignment]
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
            total = len(sentences) or 1
            return max(0.0, 1 - len(issues) / total)
        except Exception as e:
            # Log in real workflow; fallback to heuristic
            pass
    return _heuristic_style_score(text)


def structural_pattern_score(text: str) -> float:
    """Return a ratio of structural lines to total lines with a heading-order penalty."""
    lines = text.splitlines()
    if not lines:
        return 0.0

    headings: list[int] = []
    bullets = 0
    numbered = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            m = re.match(r"(#+)\s", stripped)
            if m:
                headings.append(len(m.group(1)))
        elif stripped.startswith(("-", "*", "+")):
            bullets += 1
        elif re.match(r"\d+[.)]\s", stripped):
            numbered += 1

    structured = len(headings) + bullets + numbered
    base = structured / len(lines)
    if not headings:
        return base

    jumps = sum(1 for a, b in zip(headings, headings[1:]) if b > a + 1)
    penalty = jumps / len(headings)
    return base * (1 - penalty)

# ---------------------------------------------------------------------------
# FANN-like feature scoring & anomaly detection
# ---------------------------------------------------------------------------

def _fann_features(text: str) -> list[float]:
    """Return simple numeric features for the faux FANN network."""
    words = text.lower().split()
    repeated = sum(1 for i in range(len(words) - 1) if words[i] == words[i + 1])
    unique_ratio = len(set(text)) / (len(text) or 1)

    sentence_count = sum(text.count(ch) for ch in ".!?") or 1
    word_count = len(words) or 1
    syllables = sum(_count_syllables(w) for w in words) or 1
    words_per_sentence = word_count / sentence_count
    syllables_per_word = syllables / word_count
    flesch = 206.835 - 1.015 * words_per_sentence - 84.6 * syllables_per_word
    readability = flesch / 100

    style = style_guide_score(text)
    structure = structural_pattern_score(text)

    return [
        len(text) / 1000,
        unique_ratio,
        repeated,
        readability,
        style,
        structure,
    ]


def fann_feature_dict(text: str) -> dict[str, float]:
    """Return features as a dict for workflow integration."""
    return dict(zip(FANN_FEATURE_NAMES, _fann_features(text)))


def _fann_score(text: str, weights: Optional[list[float]] = None) -> float:
    """Compute a pseudo neural score using a logistic function."""
    weights = weights or _FANN_WEIGHTS
    features = _fann_features(text)
    linear = sum(w * f for w, f in zip(weights, features))
    return 1.0 / (1.0 + math.exp(-linear))


def detect_anomalies(text: str, threshold: float = DEFAULT_ANOMALY_THRESHOLD) -> bool:
    """Return True when `text` appears anomalous using a tiny FANN model."""
    return _fann_score(text) >= threshold

# ---------------------------------------------------------------------------
# Content validation & workflow helpers
# ---------------------------------------------------------------------------

def suggest_document_type(text: str) -> str:
    """Return a suggested document type name based on keywords."""
    text_lower = text.lower()
    if "report" in text_lower:
        return "report"
    if "invoice" in text_lower:
        return "invoice"
    return "sample"


def validate_content(text: str) -> tuple[bool, dict[str, Any]]:
    """Validate content using anomaly detection and return diagnostics."""
    diagnostics = fann_feature_dict(text)
    is_valid = bool(text.strip()) and not detect_anomalies(text)
    diagnostics["is_valid"] = is_valid
    return is_valid, diagnostics


def create_validated_document(
    filename: str, data: bytes, *,
    user: str | None = None,
    project: str | None = None
) -> "DocumentModel":
    """Create a document after validating its content."""
    text = data.decode()
    is_valid, diagnostics = validate_content(text)
    if not is_valid:
        raise ValueError(f"Invalid content: {diagnostics}")
    from .documents import import_document
    return import_document(filename, data, project=project, user=user)


def suggest_export_format(content: str) -> str:
    """Return a recommended export format based on content."""
    text = content.lower()
    if "image" in text:
        return "pdf"
    if "table" in text:
        return "xlsx"
    return "markdown"

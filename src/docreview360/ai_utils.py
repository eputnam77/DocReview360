"""Utility helpers simulating AI integrations."""

from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from .documents import DocumentModel


def apply_feedback_template(template: str, text: str) -> str:
    """Insert text into the feedback template."""
    return template.replace("{text}", text)


FEEDBACK_TEMPLATES: Dict[str, str] = {"default": "Feedback: {text}"}
# Prompt-Engine templates
PROMPT_TEMPLATES: Dict[str, str] = {"default": "{text}"}


def add_feedback_template(name: str, template: str) -> None:
    """Register a new feedback template."""
    FEEDBACK_TEMPLATES[name] = template


def add_prompt_template(name: str, template: str) -> None:
    """Register a new prompt template for the Prompt-Engine."""
    PROMPT_TEMPLATES[name] = template


def render_prompt(name: str, **context: str) -> str:
    """Return a prompt rendered with the given ``context``."""
    tmpl = PROMPT_TEMPLATES.get(name, PROMPT_TEMPLATES["default"])
    return tmpl.format(**context)


def generate_feedback(name: str, text: str) -> str:
    """Return formatted feedback using the named template."""
    tmpl = FEEDBACK_TEMPLATES.get(name, FEEDBACK_TEMPLATES["default"])
    return apply_feedback_template(tmpl, text)


FANN_FEATURE_NAMES = [
    "length",
    "unique_ratio",
    "repeated",
    "readability",
    "style",
    "structure",
]


# SynthLang simulation
SYNTH_STOP_WORDS = {
    "the",
    "and",
    "is",
    "a",
    "an",
    "of",
    "in",
    "to",
}
synth_enabled = False


def synth_compress(text: str) -> str:
    """Reduce token count by removing stop words and vowels when enabled."""
    if not synth_enabled:
        return text
    words = [w for w in text.split() if w.lower() not in SYNTH_STOP_WORDS]
    no_vowels = "".join(ch for ch in " ".join(words) if ch.lower() not in "aeiou")
    return no_vowels


def _count_syllables(word: str) -> int:
    """Rough syllable estimator used for readability features."""
    import re

    groups = re.findall(r"[aeiouy]+", word.lower())
    return max(1, len(groups))


def style_guide_score(text: str) -> float:
    """Return the fraction of sentences meeting simple style rules.

    The check intentionally avoids heavy NLP dependencies yet aims to capture
    several common style issues:

    * Sentence starts with a capital letter.
    * Sentence ends with terminal punctuation (``.?!``).
    * No repeated whitespace.
    * No repeated punctuation.
    * No consecutive repeated words.
    """

    # Split on whitespace following punctuation so the punctuation is retained
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if not sentences:
        return 1.0

    good = 0
    for s in sentences:
        words = s.split()
        has_repeat = any(w1.lower() == w2.lower() for w1, w2 in zip(words, words[1:]))
        if (
            s[0].isupper()
            and s[-1] in ".!?"
            and not re.search(r"\s{2,}", s)
            and not re.search(r"[.!?]{2,}", s)
            and not has_repeat
        ):
            good += 1
    return good / len(sentences)


def structural_pattern_score(text: str) -> float:
    """Return a ratio of structural lines to total lines.

    Structural lines include Markdown headings, bullet lists and numbered
    lists.  This provides a slightly richer signal than simply counting
    headings.
    """

    lines = text.splitlines()
    if not lines:
        return 0.0
    headings = sum(1 for line in lines if line.strip().startswith("#"))
    bullets = sum(1 for line in lines if line.strip().startswith(("-", "*", "+")))
    numbered = sum(1 for line in lines if re.match(r"\d+[.)]\s", line.strip()))
    structured = headings + bullets + numbered
    return structured / len(lines)


def _fann_features(text: str) -> list[float]:
    """Return simple numeric features for the faux FANN network.

    Features
    --------
    * Normalised length (thousands of characters)
    * Ratio of unique characters
    * Repeated consecutive word count
    * Flesch reading ease score (scaled 0-1)
    * Style guide adherence score
    * Structural pattern score
    """

    words = text.lower().split()
    repeated = sum(1 for i in range(len(words) - 1) if words[i] == words[i + 1])
    unique_ratio = len(set(text)) / (len(text) or 1)

    sentence_count = sum(text.count(ch) for ch in ".!?") or 1
    word_count = len(words) or 1
    syllables = sum(_count_syllables(w) for w in words) or 1
    words_per_sentence = word_count / sentence_count
    syllables_per_word = syllables / word_count
    flesch = 206.835 - 1.015 * words_per_sentence - 84.6 * syllables_per_word
    readability = flesch / 100  # scale to roughly 0-1

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


_FANN_WEIGHTS = [0.0, -0.1, 1.2, -0.1, -0.2, -0.2]


def _fann_score(text: str) -> float:
    """Compute a pseudo neural score using a logistic function."""
    features = _fann_features(text)
    linear = sum(w * f for w, f in zip(_FANN_WEIGHTS, features))
    return 1.0 / (1.0 + math.exp(-linear))


def detect_anomalies(text: str, threshold: float = 0.7) -> bool:
    """Return ``True`` when ``text`` appears anomalous using a tiny FANN model."""
    score = _fann_score(text)
    return score >= threshold


def suggest_document_type(text: str) -> str:
    """Return a suggested document type name based on keywords."""
    text_lower = text.lower()
    if "report" in text_lower:
        return "report"
    if "invoice" in text_lower:
        return "invoice"
    return "sample"


def validate_content(text: str) -> bool:
    """Very basic content validation using anomaly detection."""
    if not text.strip():
        return False
    if detect_anomalies(text):
        return False
    return True


def create_validated_document(
    filename: str, data: bytes, *, user: str | None = None, project: str | None = None
) -> "DocumentModel":
    """Create a document after validating its content."""
    text = data.decode()
    if not validate_content(text):
        raise ValueError("Invalid content")
    from .documents import import_document

    return import_document(filename, data, project=project, user=user)


def suggest_export_format(content: str) -> str:
    """Return a recommended export format based on ``content``."""
    text = content.lower()
    if "image" in text:
        return "pdf"
    if "table" in text:
        return "xlsx"
    return "markdown"

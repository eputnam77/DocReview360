"""Document pre-flight validation checks.

Implements AI-assisted review helpers described in the release roadmap Section B:

* Acronym validation (ensure every ALL-CAPS token is defined in the document)
* Heading structure validation (H1 → H2 → H3 nesting, no skipped levels)
* Plain language scoring (Flesch Reading Ease approximation)
* AI style validation pass (toggleable via ``DOCREVIEW360_AI_STYLE=1``)
* Pre-flight composite check before phase advancement

None of these checks require external network calls; they are fully
deterministic so they work in air-gapped environments.  The optional AI-style
check can be connected to a real model via environment variable in the future.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "AcronymIssue",
    "HeadingIssue",
    "PlainLanguageScore",
    "StyleIssue",
    "PreflightResult",
    "validate_acronyms",
    "validate_heading_structure",
    "score_plain_language",
    "validate_style",
    "preflight_validate",
]

# ---------------------------------------------------------------------------
# Acronym validation
# ---------------------------------------------------------------------------

_ACRONYM_RE = re.compile(r"\b([A-Z]{2,})\b")
# Match "ACRONYM (expansion)" or "(expansion) ACRONYM" patterns
_DEFINITION_RE = re.compile(r"\b([A-Z]{2,})\s*\(([^)]+)\)")
_EXPANSION_RE = re.compile(r"\(([^)]+)\)\s+([A-Z]{2,})")


@dataclass
class AcronymIssue:
    """An acronym found in the text that is not defined within the document."""

    acronym: str
    occurrences: int


def validate_acronyms(text: str) -> list[AcronymIssue]:
    """Return a list of acronyms that appear in *text* but are never defined.

    An acronym is considered *defined* if it appears in the form
    ``ACRONYM (expansion)`` or ``(expansion) ACRONYM`` at least once.

    Parameters
    ----------
    text:
        The full document text to inspect.

    Returns
    -------
    list[AcronymIssue]
        Each entry represents an undefined acronym together with the number of
        times it appears in the document.  An empty list means all acronyms are
        defined.
    """
    # Collect defined acronyms
    defined: set[str] = set()
    for m in _DEFINITION_RE.finditer(text):
        defined.add(m.group(1))
    for m in _EXPANSION_RE.finditer(text):
        defined.add(m.group(2))

    # Count all acronym occurrences
    counts: dict[str, int] = {}
    for m in _ACRONYM_RE.finditer(text):
        token = m.group(1)
        # Skip tokens that look like Roman numerals or all-cap words <= 1 char
        if token in defined:
            continue
        counts[token] = counts.get(token, 0) + 1

    return [AcronymIssue(acronym=acro, occurrences=cnt) for acro, cnt in sorted(counts.items())]


# ---------------------------------------------------------------------------
# Heading structure validation
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


@dataclass
class HeadingIssue:
    """A structural problem detected in the heading hierarchy."""

    line_number: int
    heading_text: str
    level: int
    issue: str  # e.g. "skipped level" or "multiple H1"


def validate_heading_structure(text: str) -> list[HeadingIssue]:
    """Return structural issues found in the Markdown heading hierarchy.

    Checks performed:

    * No skipped heading levels (e.g. H1 → H3 without an H2 in between).
    * At most one H1 heading per document.

    Parameters
    ----------
    text:
        Markdown document text.

    Returns
    -------
    list[HeadingIssue]
        Issues found, in document order.  Empty list means the heading
        structure is well-formed.
    """
    issues: list[HeadingIssue] = []
    prev_level = 0
    h1_count = 0

    lines = text.splitlines()
    for line_idx, line in enumerate(lines, start=1):
        m = _HEADING_RE.match(line)
        if not m:
            continue
        level = len(m.group(1))
        heading_text = m.group(2).strip()

        if level == 1:
            h1_count += 1
            if h1_count > 1:
                issues.append(
                    HeadingIssue(
                        line_number=line_idx,
                        heading_text=heading_text,
                        level=level,
                        issue="multiple H1 headings",
                    )
                )

        if prev_level > 0 and level > prev_level + 1:
            issues.append(
                HeadingIssue(
                    line_number=line_idx,
                    heading_text=heading_text,
                    level=level,
                    issue=f"skipped heading level (H{prev_level} -> H{level})",
                )
            )

        prev_level = level

    return issues


# ---------------------------------------------------------------------------
# Plain language scoring (Flesch Reading Ease approximation)
# ---------------------------------------------------------------------------

_SENTENCE_END_RE = re.compile(r"[.!?]+")
_WORD_RE = re.compile(r"\b[a-zA-Z]+\b")
_VOWEL_RE = re.compile(r"[aeiouAEIOU]")


def _count_syllables(word: str) -> int:
    """Estimate syllable count for a single word."""
    word = word.lower()
    count = len(_VOWEL_RE.findall(word))
    # Subtract silent trailing 'e'
    if word.endswith("e") and count > 1:
        count -= 1
    return max(1, count)


@dataclass
class PlainLanguageScore:
    """Readability metrics for a document."""

    flesch_reading_ease: float
    grade_level: str
    avg_words_per_sentence: float
    avg_syllables_per_word: float
    total_words: int
    total_sentences: int
    recommendation: str


def score_plain_language(text: str) -> PlainLanguageScore:
    """Compute a Flesch Reading Ease score and plain-language grade for *text*.

    The Flesch Reading Ease formula:
        206.835 − 1.015 × (words/sentences) − 84.6 × (syllables/words)

    Higher scores indicate easier reading.  Returns sensible defaults for
    very short or empty documents.
    """
    sentences = [s.strip() for s in _SENTENCE_END_RE.split(text) if s.strip()]
    words = _WORD_RE.findall(text)

    total_sentences = max(1, len(sentences))
    total_words = len(words)

    if total_words == 0:
        return PlainLanguageScore(
            flesch_reading_ease=0.0,
            grade_level="N/A",
            avg_words_per_sentence=0.0,
            avg_syllables_per_word=0.0,
            total_words=0,
            total_sentences=0,
            recommendation="Document has no readable text.",
        )

    total_syllables = sum(_count_syllables(w) for w in words)
    avg_words_per_sentence = total_words / total_sentences
    avg_syllables_per_word = total_syllables / total_words

    score = 206.835 - 1.015 * avg_words_per_sentence - 84.6 * avg_syllables_per_word
    score = round(max(0.0, min(100.0, score)), 1)

    if score >= 90:
        grade_level = "5th grade"
        recommendation = "Very easy to read. Appropriate for all audiences."
    elif score >= 80:
        grade_level = "6th grade"
        recommendation = "Easy to read. Suitable for general public."
    elif score >= 70:
        grade_level = "7th grade"
        recommendation = "Fairly easy. Acceptable for most audiences."
    elif score >= 60:
        grade_level = "8th–9th grade"
        recommendation = "Plain English. Standard for web content."
    elif score >= 50:
        grade_level = "10th–12th grade"
        recommendation = "Fairly difficult. Consider simplifying sentences."
    elif score >= 30:
        grade_level = "College"
        recommendation = "Difficult. Simplify vocabulary and shorten sentences."
    else:
        grade_level = "College graduate"
        recommendation = "Very difficult. Significant plain-language revision recommended."

    return PlainLanguageScore(
        flesch_reading_ease=score,
        grade_level=grade_level,
        avg_words_per_sentence=round(avg_words_per_sentence, 1),
        avg_syllables_per_word=round(avg_syllables_per_word, 2),
        total_words=total_words,
        total_sentences=total_sentences,
        recommendation=recommendation,
    )


# ---------------------------------------------------------------------------
# AI style validation (toggleable)
# ---------------------------------------------------------------------------

_AI_STYLE_ENABLED_ENV = "DOCREVIEW360_AI_STYLE"

# Simple rule-based style checks that stand in for an AI model.
# Each entry: (pattern, message)
_STYLE_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(utilize)\b", re.IGNORECASE), "prefer 'use' over 'utilize'"),
    (re.compile(r"\b(in order to)\b", re.IGNORECASE), "prefer 'to' over 'in order to'"),
    (re.compile(r"\b(at this point in time)\b", re.IGNORECASE), "prefer 'now' over 'at this point in time'"),
    (re.compile(r"\b(due to the fact that)\b", re.IGNORECASE), "prefer 'because' over 'due to the fact that'"),
    (re.compile(r"\b(it is important to note that)\b", re.IGNORECASE), "remove filler phrase 'it is important to note that'"),
    (re.compile(r"\b(absolutely|definitely|certainly|really|very)\b", re.IGNORECASE), "avoid filler intensifiers"),
    (re.compile(r"\b(basically|essentially|actually)\b", re.IGNORECASE), "avoid hedging filler words"),
]


@dataclass
class StyleIssue:
    """A single style suggestion for a span of text."""

    line_number: int
    matched_text: str
    suggestion: str


def is_ai_style_enabled() -> bool:
    """Return ``True`` when the AI style validation pass is enabled."""
    val = os.environ.get(_AI_STYLE_ENABLED_ENV, "0").strip().lower()
    return val in {"1", "true", "yes", "on"}


def validate_style(text: str, *, force: bool = False) -> list[StyleIssue]:
    """Run the (toggleable) style validation pass over *text*.

    When the ``DOCREVIEW360_AI_STYLE`` environment variable is not set to a
    truthy value, this function returns an empty list unless *force* is
    ``True``.  This keeps the check opt-in so it does not slow down every
    workflow.

    Parameters
    ----------
    text:
        Full document text to check.
    force:
        Bypass the environment-flag gate and always run checks.

    Returns
    -------
    list[StyleIssue]
        Style issues found, in document order.
    """
    if not force and not is_ai_style_enabled():
        return []

    issues: list[StyleIssue] = []
    lines = text.splitlines()
    for line_idx, line in enumerate(lines, start=1):
        for pattern, suggestion in _STYLE_RULES:
            for m in pattern.finditer(line):
                issues.append(
                    StyleIssue(
                        line_number=line_idx,
                        matched_text=m.group(0),
                        suggestion=suggestion,
                    )
                )
    return issues


# ---------------------------------------------------------------------------
# Pre-flight composite validation
# ---------------------------------------------------------------------------


@dataclass
class PreflightResult:
    """Composite pre-flight validation result for a document before phase advancement.

    All checks are always executed; callers decide what severity threshold to
    enforce.
    """

    passed: bool
    acronym_issues: list[AcronymIssue] = field(default_factory=list)
    heading_issues: list[HeadingIssue] = field(default_factory=list)
    plain_language: PlainLanguageScore | None = None
    style_issues: list[StyleIssue] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation of this result."""
        return {
            "passed": self.passed,
            "acronym_issues": [
                {"acronym": i.acronym, "occurrences": i.occurrences}
                for i in self.acronym_issues
            ],
            "heading_issues": [
                {
                    "line_number": i.line_number,
                    "heading_text": i.heading_text,
                    "level": i.level,
                    "issue": i.issue,
                }
                for i in self.heading_issues
            ],
            "plain_language": (
                {
                    "flesch_reading_ease": self.plain_language.flesch_reading_ease,
                    "grade_level": self.plain_language.grade_level,
                    "avg_words_per_sentence": self.plain_language.avg_words_per_sentence,
                    "avg_syllables_per_word": self.plain_language.avg_syllables_per_word,
                    "total_words": self.plain_language.total_words,
                    "total_sentences": self.plain_language.total_sentences,
                    "recommendation": self.plain_language.recommendation,
                }
                if self.plain_language
                else None
            ),
            "style_issues": [
                {
                    "line_number": i.line_number,
                    "matched_text": i.matched_text,
                    "suggestion": i.suggestion,
                }
                for i in self.style_issues
            ],
            "errors": self.errors,
        }


def preflight_validate(
    text: str,
    *,
    min_reading_ease: float = 0.0,
    require_no_undefined_acronyms: bool = False,
    require_valid_headings: bool = True,
) -> PreflightResult:
    """Run all pre-flight checks on *text* and return a composite result.

    Parameters
    ----------
    text:
        Full document content to validate.
    min_reading_ease:
        Minimum Flesch Reading Ease score required to pass (0–100).
        A value of 0 means no readability threshold is enforced.
    require_no_undefined_acronyms:
        When ``True``, any undefined acronym causes ``passed`` to be
        ``False``.
    require_valid_headings:
        When ``True``, any heading structure issue causes ``passed`` to be
        ``False``.

    Returns
    -------
    PreflightResult
        Composite result; ``passed`` is ``True`` only if every enabled check
        passes.
    """
    errors: list[str] = []

    acronym_issues = validate_acronyms(text)
    if require_no_undefined_acronyms and acronym_issues:
        errors.append(
            f"{len(acronym_issues)} undefined acronym(s) found: "
            + ", ".join(i.acronym for i in acronym_issues[:5])
        )

    heading_issues = validate_heading_structure(text)
    if require_valid_headings and heading_issues:
        errors.append(
            f"{len(heading_issues)} heading structure issue(s): "
            + "; ".join(i.issue for i in heading_issues[:3])
        )

    pl_score = score_plain_language(text)
    if min_reading_ease > 0 and pl_score.flesch_reading_ease < min_reading_ease:
        errors.append(
            f"Reading ease {pl_score.flesch_reading_ease} is below required {min_reading_ease}"
        )

    style_issues = validate_style(text)

    return PreflightResult(
        passed=len(errors) == 0,
        acronym_issues=acronym_issues,
        heading_issues=heading_issues,
        plain_language=pl_score,
        style_issues=style_issues,
        errors=errors,
    )

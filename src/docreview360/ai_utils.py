"""Utility helpers simulating AI integrations for scoring, validation, and workflow routing.

This module contains:
- Prompt and feedback template management.
- Lightweight SynthLang text compression simulation.
- Faux FANN-style scoring for style, structure, and readability.
- Heuristic and GovDocVerify-based style checks.
- Workflow-friendly helpers for anomaly detection,
  document type suggestions, and export format hints.

Dependencies:
- GovDocVerify (optional). Falls back to internal heuristics when unavailable.
"""

from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING, Any, Dict, Optional

from .ml.features import (
    CUSTOM_STYLE_RULES,
    FANN_FEATURE_NAMES,
    count_syllables,
    quality_features,
    structural_pattern_score,
    style_guide_score,
)
from .quality import QUALITY_FLAG_NAMES, quality_assessment

# Backwards-compatible alias for tests patching GovDocVerify integration.
try:  # pragma: no cover - defensive re-export
    from .ml.features import _gov_run as _gov_run  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - fall back when attribute missing
    _gov_run = None


def _count_syllables(word: str) -> int:
    """Backward compatible alias for :func:`docreview360.ml.features.count_syllables`."""

    return count_syllables(word)

if TYPE_CHECKING:
    from .documents import DocumentModel

# ---------------------------------------------------------------------------
# Configurable constants & defaults
# ---------------------------------------------------------------------------

# Default stop words for SynthLang compression
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

# FANN weights (configurable)
_FANN_WEIGHTS = [0.0, -0.1, 1.2, -0.1, -0.2, -0.2]

# Default anomaly detection threshold
DEFAULT_ANOMALY_THRESHOLD = 0.7

# Feedback and prompt templates
FEEDBACK_TEMPLATES: Dict[str, str] = {"default": "Feedback: {text}"}
PROMPT_TEMPLATES: Dict[str, str] = {"default": "{text}"}

# SynthLang enable flag
synth_enabled = False

# ---------------------------------------------------------------------------
# Template management
# ---------------------------------------------------------------------------


_FEEDBACK_PLACEHOLDER = re.compile(r"(?<!\{)\{text\}(?!\})")


def apply_feedback_template(template: str, text: str) -> str:
    """Insert `text` into the feedback template."""
    if not _FEEDBACK_PLACEHOLDER.search(template):
        raise ValueError("Feedback template must contain '{text}' placeholder.")
    return template.replace("{text}", text)


def add_feedback_template(name: str, template: str) -> None:
    """Register a new feedback template."""
    if not _FEEDBACK_PLACEHOLDER.search(template):
        raise ValueError("Feedback template must contain '{text}' placeholder.")
    FEEDBACK_TEMPLATES[name] = template


def add_prompt_template(name: str, template: str) -> None:
    """Register a new prompt template for the Prompt-Engine."""
    # ``str.format`` uses double braces to escape literal ``{`` and ``}``.  The
    # previous implementation incorrectly treated strings like ``"{{name}}`` as
    # containing a real placeholder which later resulted in ``{name}`` appearing
    # verbatim when rendering.  Use negative look-arounds to ensure braces are
    # not escaped and require at least one real placeholder.
    placeholder = re.search(r"(?<!\{)\{[a-zA-Z_][a-zA-Z0-9_]*\}(?!\})", template)
    if not placeholder:
        raise ValueError("Prompt template must contain at least one placeholder.")
    PROMPT_TEMPLATES[name] = template


def render_prompt(name: str, **context: str) -> str:
    """Return a prompt rendered with the given `context`."""
    tmpl = PROMPT_TEMPLATES.get(name, PROMPT_TEMPLATES["default"])
    try:
        return tmpl.format(**context)
    except KeyError as e:
        missing = e.args[0]
        raise ValueError(f"Missing placeholder in prompt context: {missing}") from e


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
    if SYNTH_STOP_WORDS:
        pattern = re.compile(
            r"\b(" + "|".join(re.escape(w) for w in SYNTH_STOP_WORDS) + r")\b",
            re.I,
        )
        cleaned = pattern.sub("", text)
    else:
        # Building a regex with an empty group results in ``re.error``.  When no
        # stop words are configured we simply operate on the original text.
        cleaned = text
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    no_vowels = "".join(ch for ch in cleaned if ch.lower() not in "aeiou")
    return no_vowels


# ---------------------------------------------------------------------------
# FANN-like feature scoring & anomaly detection
# ---------------------------------------------------------------------------


def _fann_features(text: str) -> list[float]:
    """Return faux-FANN features sourced from the ML feature adapter."""

    payload = quality_features(text)
    legacy = payload.get("legacy", {}).get("fann")
    if not legacy:
        raise ValueError("quality feature payload missing legacy FANN mapping")
    return [legacy[name] for name in FANN_FEATURE_NAMES]


def fann_feature_dict(text: str) -> dict[str, float]:
    """Return features as a dict for workflow integration."""

    payload = quality_features(text)
    legacy = payload.get("legacy", {}).get("fann")
    if not legacy:
        raise ValueError("quality feature payload missing legacy FANN mapping")
    return dict(legacy)


def _fann_score(text: str, weights: Optional[list[float]] = None) -> float:
    """Compute a pseudo neural score using a logistic function."""
    # ``weights`` previously relied on the truthiness of the supplied list.
    # This meant that calling ``_fann_score(text, [])`` would fall back to the
    # global ``_FANN_WEIGHTS`` instead of using the explicitly provided empty
    # sequence.  Test suite tasks intentionally exercise the ability to supply
    # a zeroed weight vector to obtain a neutral (0.5) score, so we need to
    # distinguish between ``None`` and an empty list.
    weights = _FANN_WEIGHTS if weights is None else weights
    features = _fann_features(text)
    linear = sum(w * f for w, f in zip(weights, features))
    return 1.0 / (1.0 + math.exp(-linear))


def detect_anomalies(text: str, threshold: float = DEFAULT_ANOMALY_THRESHOLD) -> bool:
    """Return ``True`` when any quality flag exceeds ``threshold``."""

    assessment = quality_assessment(text)
    return any(flag >= threshold for flag in assessment.flags)


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


def validate_content(
    text: str, *, return_diagnostics: bool = False
) -> bool | tuple[bool, dict[str, Any]]:
    """Validate ``text`` and optionally return diagnostic details.

    The original implementation returned a ``(bool, diagnostics)`` tuple
    unconditionally.  Most callers, however, only care about the boolean
    flag.  Returning a tuple forced them to unpack the value or ended up
    always evaluating as ``True`` in boolean context.  The function now
    returns the validation flag by default and only includes the diagnostic
    information when explicitly requested via ``return_diagnostics=True``.
    """

    assessment = quality_assessment(text)
    diagnostics = fann_feature_dict(text)
    diagnostics["quality"] = {
        "score": assessment.score,
        "raw_score": assessment.raw_score,
        "flags": dict(zip(QUALITY_FLAG_NAMES, assessment.flags)),
    }
    has_text = bool(text.strip())
    has_anomaly = any(flag >= DEFAULT_ANOMALY_THRESHOLD for flag in assessment.flags)
    is_valid = has_text and not has_anomaly
    diagnostics["is_valid"] = is_valid
    if return_diagnostics:
        return is_valid, diagnostics
    return is_valid


def create_validated_document(
    filename: str, data: bytes, *, user: str | None = None, project: str | None = None
) -> "DocumentModel":
    """Create a document after validating its content."""
    try:
        text = data.decode()
    except UnicodeDecodeError as exc:
        raise ValueError("data must be valid UTF-8") from exc
    is_valid, diagnostics = validate_content(text, return_diagnostics=True)
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

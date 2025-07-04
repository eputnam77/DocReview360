"""Utility helpers simulating AI integrations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:  # pragma: no cover - hints only
    from .documents import DocumentModel


def apply_feedback_template(template: str, text: str) -> str:
    """Insert text into the feedback template."""
    return template.replace("{text}", text)


FEEDBACK_TEMPLATES: Dict[str, str] = {"default": "Feedback: {text}"}


def add_feedback_template(name: str, template: str) -> None:
    """Register a new feedback template."""
    FEEDBACK_TEMPLATES[name] = template


def generate_feedback(name: str, text: str) -> str:
    """Return formatted feedback using the named template."""
    tmpl = FEEDBACK_TEMPLATES.get(name, FEEDBACK_TEMPLATES["default"])
    return apply_feedback_template(tmpl, text)


# SynthLang simulation
synth_enabled = False


def synth_compress(text: str) -> str:
    """Reduce token count by removing vowels when enabled."""
    if not synth_enabled:
        return text
    return "".join(ch for ch in text if ch.lower() not in "aeiou")


def detect_anomalies(text: str) -> bool:
    """Very naive anomaly detection checking for repeated words."""
    words = text.lower().split()
    for i in range(len(words) - 1):
        if words[i] == words[i + 1]:
            return True
    return False


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

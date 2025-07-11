from __future__ import annotations

"""Minimal NeMo-Guardrails style PII checker."""

import re


def contains_pii(text: str) -> bool:
    """Return ``True`` if the text appears to contain PII such as SSNs."""

    ssn_pattern = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
    return bool(ssn_pattern.search(text))

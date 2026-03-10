# SPDX-License-Identifier: MIT
"""Editor compliance helpers (Task 150)."""

from __future__ import annotations

from typing import Dict

from .fed_numbering import apply_numbering, can_toggle_numbering
from .grammar_plugin import check_grammar


def lint_document(text: str) -> list[str]:
    """Return grammar issues for ``text``."""
    issues = check_grammar(text)
    return issues


def toggle_numbering(
    text: str,
    mapping: Dict[str, str],
    role: str,
    rbac: Dict[str, Dict[str, bool]],
) -> str:
    """Return text with numbering applied if role is allowed."""
    if not can_toggle_numbering(role, rbac):
        return text
    return apply_numbering(text, mapping)

# SPDX-License-Identifier: MIT
"""Grammar-checker plug-in."""

from __future__ import annotations

from typing import Any, List


def check_grammar(text: str) -> List[str]:
    """Return a list of simple grammar issues."""
    errors: List[str] = []
    words = text.split()
    for i in range(len(words) - 1):
        if words[i] == words[i + 1]:
            errors.append(f"repeated word '{words[i]}'")
    return errors


def register(registry: Any) -> None:
    """Register the grammar checker with the plugin registry."""
    registry.register("grammar-checker", check_grammar)

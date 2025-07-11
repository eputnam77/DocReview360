"""TipTap plugin wrappers: template linter and numbering helper."""

from __future__ import annotations

from typing import Any, Dict, List

from .fed_numbering import apply_numbering
from .tiptap import markdown_to_tiptap, tiptap_to_markdown


def lint_template_plugin(data: Dict[str, Any], rules: Dict[str, List[str]]) -> List[str]:
    """Return a list of lint warnings for missing required headings."""
    markdown = tiptap_to_markdown(data)
    issues: List[str] = []
    for heading in rules.get("required_headings", []):
        if f"# {heading}" not in markdown:
            issues.append(f"missing heading '{heading}'")
    return issues


def numbering_plugin(data: Dict[str, Any], mapping: Dict[str, str]) -> Dict[str, Any]:
    """Return TipTap JSON with numbered headings using ``mapping``."""
    markdown = tiptap_to_markdown(data)
    numbered = apply_numbering(markdown, mapping)
    return markdown_to_tiptap(numbered)

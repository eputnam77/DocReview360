"""WCAG 2.1 AA audit helpers."""

from __future__ import annotations

import re
from typing import List

_IMG_TAG = re.compile(r"<img [^>]*>", re.IGNORECASE)
_ALT_ATTR = re.compile(r"alt=\"[^\"]*\"")
_BUTTON_TAG = re.compile(r"<button([^>]*)>(.*?)</button>", re.IGNORECASE | re.DOTALL)
_ARIA_LABEL = re.compile(r"aria-label=\"[^\"]*\"")


def audit_html(html: str) -> List[str]:
    """Return a list of accessibility issues found in ``html``."""
    issues: List[str] = []
    for img_match in _IMG_TAG.findall(html):
        if not _ALT_ATTR.search(img_match):
            issues.append("image missing alt text")
    for attrs, body in _BUTTON_TAG.findall(html):
        if not _ARIA_LABEL.search(attrs) and not body.strip():
            issues.append("button missing label")
    return issues

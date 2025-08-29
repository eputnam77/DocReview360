"""WCAG 2.1 AA audit helpers."""

from __future__ import annotations

import re
from typing import List

_IMG_TAG = re.compile(r"<img [^>]*>", re.IGNORECASE)
# ``alt`` attributes may be quoted or unquoted.  The previous pattern only
# recognised quoted variants which wrongly flagged valid markup like
# ``<img alt=logo>``.  Allow unquoted values that end at whitespace or ``>``.
_ALT_ATTR = re.compile(r"alt\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+)", re.IGNORECASE)
_BUTTON_TAG = re.compile(r"<button([^>]*)>(.*?)</button>", re.IGNORECASE | re.DOTALL)
# ``aria-label`` should contain at least one character; an empty attribute is
# effectively the same as having no label at all.  The previous regular
# expression used ``*`` which matched empty strings and therefore failed to
# flag ``aria-label=""`` as an issue.
_ARIA_LABEL = re.compile(r"aria-label\s*=\s*(?:\"[^\"]+\"|'[^']+')", re.IGNORECASE)


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

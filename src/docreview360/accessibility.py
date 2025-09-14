"""WCAG 2.1 AA audit helpers."""

from __future__ import annotations

import re
from typing import List

# ``<img>`` tags without any attributes such as ``<img>`` previously failed to
# match because a space was required after the tag name.  Use a word boundary so
# both bare tags and those with attributes are handled uniformly.
_IMG_TAG = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
# ``alt`` attributes may be quoted or unquoted.  The previous pattern only
# recognised quoted variants which wrongly flagged valid markup like
# ``<img alt=logo>``.  Allow unquoted values that end at whitespace or ``>``.
_ALT_ATTR = re.compile(
    r"alt\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>/]+))",
    re.IGNORECASE,
)
_BUTTON_TAG = re.compile(r"<button([^>]*)>(.*?)</button>", re.IGNORECASE | re.DOTALL)
# ``aria-label`` should contain at least one character; an empty attribute is
# effectively the same as having no label at all.  The previous regular
# expression used ``*`` which matched empty strings and therefore failed to
# flag ``aria-label=""`` as an issue.
# ``aria-label`` attributes may appear without quotes.  The former pattern only
# matched quoted values which caused valid markup like ``aria-label=Submit`` to
# be reported as missing a label.  Allow a third capture group for unquoted
# values while still ensuring at least one character is present.
_ARIA_LABEL = re.compile(
    r"aria-label\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>/\'\"]+))",
    re.IGNORECASE,
)


def audit_html(html: str) -> List[str]:
    """Return a list of accessibility issues found in ``html``."""
    issues: List[str] = []
    for img_match in _IMG_TAG.findall(html):
        m = _ALT_ATTR.search(img_match)
        # Treat missing ``alt`` attributes and those containing only whitespace
        # as issues because they provide no descriptive alternative text.
        if not m or not (m.group(1) or m.group(2) or m.group(3) or "").strip():
            issues.append("image missing alt text")
    for attrs, body in _BUTTON_TAG.findall(html):
        # Strip any nested HTML tags when determining if the button has
        # visible text.  Previously ``<button><span></span></button>`` was
        # treated as having a label because the inner markup wasn't removed.
        text = re.sub(r"<[^>]+>", "", body).strip()
        m = _ARIA_LABEL.search(attrs)
        label = ""
        if m:
            label = (m.group(1) or m.group(2) or m.group(3) or "").strip()
        if not label and not text:
            issues.append("button missing label")
    return issues

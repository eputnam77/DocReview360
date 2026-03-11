# SPDX-License-Identifier: MIT
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
# Disallow quotes within unquoted ``alt`` values and ensure the attribute ends
# before any invalid characters like stray quotes.  Without the lookahead a tag
# such as ``alt=foo"`` would be interpreted as having the value ``foo`` even
# though the trailing quote renders the markup invalid.
_ALT_ATTR = re.compile(
    r"alt\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>/\'\"]+))(?=[\s>/])",
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


# ---------------------------------------------------------------------------
# Extended WCAG 2.1 AA / Section 508 scanner
# ---------------------------------------------------------------------------

from dataclasses import dataclass, field as _field
from datetime import datetime, timezone

_EMPTY_LINK = re.compile(r"<a\b[^>]*>\s*(?:<[^>]+>\s*)*</a>", re.IGNORECASE | re.DOTALL)
_HEADING = re.compile(r"<h([1-6])\b", re.IGNORECASE)
_FORM_INPUT = re.compile(r"<input\b[^>]*/?>", re.IGNORECASE)
_INPUT_ID = re.compile(r'\bid\s*=\s*["\']?([^"\'>\s]+)', re.IGNORECASE)
_LABEL_FOR = re.compile(r'<label\b[^>]*\bfor\s*=\s*["\']?([^"\'>\s]+)', re.IGNORECASE)
_LANG_ATTR = re.compile(r'<html\b[^>]*\blang\s*=\s*["\']?([^"\'>\s]+)', re.IGNORECASE)


@dataclass
class AccessibilityViolation:
    criterion: str
    severity: str  # "error" | "warning"
    description: str
    element: str = ""


@dataclass
class AccessibilityScanResult:
    document_id: str
    checked_at: str
    wcag_level: str  # "A" | "AA" | "AAA"
    violations: List[AccessibilityViolation] = _field(default_factory=list)
    passes: List[str] = _field(default_factory=list)
    score: int = 100


def scan_document_accessibility(
    content: str, doc_id: str, wcag_level: str = "AA"
) -> AccessibilityScanResult:
    """Scan document content for WCAG 2.1 AA / Section 508 accessibility issues.

    Returns an AccessibilityScanResult with violations, passes, and an overall score.
    Score = 100 − (errors × 10 + warnings × 3), clamped to [0, 100].
    """
    violations: List[AccessibilityViolation] = []
    passes: List[str] = []

    # 1.1.1 — Non-text content: images need alt text
    img_issues = audit_html(content)
    if "image missing alt text" in img_issues:
        violations.append(
            AccessibilityViolation(
                criterion="WCAG 1.1.1",
                severity="error",
                description="One or more images are missing alt text",
                element="<img>",
            )
        )
    else:
        passes.append("WCAG 1.1.1 — Images have alt text")

    # 4.1.2 — Name, Role, Value: buttons need accessible names
    if "button missing label" in img_issues:
        violations.append(
            AccessibilityViolation(
                criterion="WCAG 4.1.2",
                severity="error",
                description="One or more buttons are missing an accessible name (aria-label or text)",
                element="<button>",
            )
        )
    else:
        passes.append("WCAG 4.1.2 — Buttons have accessible names")

    # 2.4.4 — Link purpose: empty links are problematic
    empty_links = _EMPTY_LINK.findall(content)
    if empty_links:
        violations.append(
            AccessibilityViolation(
                criterion="WCAG 2.4.4",
                severity="error",
                description=f"{len(empty_links)} link(s) have no text content",
                element="<a>",
            )
        )
    else:
        passes.append("WCAG 2.4.4 — Links have descriptive text")

    # 1.3.1 — Info and Relationships: check heading hierarchy
    headings = [int(m) for m in _HEADING.findall(content)]
    if headings:
        prev = headings[0]
        skip_detected = False
        for level in headings[1:]:
            if level > prev + 1:
                skip_detected = True
                break
            prev = level
        if skip_detected:
            violations.append(
                AccessibilityViolation(
                    criterion="WCAG 1.3.1",
                    severity="warning",
                    description="Heading levels are skipped (e.g., h1 → h3), disrupting screen reader navigation",
                    element="<hN>",
                )
            )
        else:
            passes.append("WCAG 1.3.1 — Heading hierarchy is sequential")
    else:
        passes.append("WCAG 1.3.1 — No headings to check")

    # 3.1.1 — Language of page: <html lang="..."> should be present
    if not _LANG_ATTR.search(content):
        violations.append(
            AccessibilityViolation(
                criterion="WCAG 3.1.1",
                severity="warning",
                description="Missing lang attribute on <html> element",
                element="<html>",
            )
        )
    else:
        passes.append("WCAG 3.1.1 — Language attribute is set")

    # 1.3.5 — Form inputs should have associated labels
    input_ids = set(_INPUT_ID.findall(content))
    label_fors = set(_LABEL_FOR.findall(content))
    unlabelled = input_ids - label_fors
    if unlabelled:
        violations.append(
            AccessibilityViolation(
                criterion="WCAG 1.3.1",
                severity="warning",
                description=f"{len(unlabelled)} form input(s) appear to lack associated <label> elements",
                element="<input>",
            )
        )
    else:
        passes.append("WCAG 1.3.5 — Form inputs have labels")

    # Compute score
    errors = sum(1 for v in violations if v.severity == "error")
    warnings = sum(1 for v in violations if v.severity == "warning")
    score = max(0, 100 - errors * 10 - warnings * 3)

    return AccessibilityScanResult(
        document_id=doc_id,
        checked_at=datetime.now(timezone.utc).isoformat(),
        wcag_level=wcag_level,
        violations=violations,
        passes=passes,
        score=score,
    )


def scan_result_to_dict(result: AccessibilityScanResult) -> dict:
    """Convert an AccessibilityScanResult to a JSON-serialisable dict."""
    return {
        "document_id": result.document_id,
        "checked_at": result.checked_at,
        "wcag_level": result.wcag_level,
        "score": result.score,
        "violations": [
            {
                "criterion": v.criterion,
                "severity": v.severity,
                "description": v.description,
                "element": v.element,
            }
            for v in result.violations
        ],
        "passes": result.passes,
    }

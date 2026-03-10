# SPDX-License-Identifier: MIT
"""Regulatory citation format checker.

Extracts and validates regulatory citations from document text, checking whether
cited standards and regulations exist in a known catalog and are correctly formatted.

Supported citation families:
- U.S. Code of Federal Regulations (21 CFR, 47 CFR, etc.)
- ISO standards (ISO 13485, ISO 14971, etc.)
- IEC standards (IEC 62304, IEC 62366, etc.)
- EU Medical Device Regulation (EU MDR 2017/745)
- EU In Vitro Diagnostic Regulation (EU IVDR 2017/746)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Known regulatory catalog
# ---------------------------------------------------------------------------

# FDA-relevant CFR parts (Title 21 — food and drugs; Title 47 — communications)
_KNOWN_CFR: dict[int, set[int]] = {
    21: {11, 50, 54, 56, 58, 312, 314, 600, 801, 803, 806, 807, 812, 814, 816, 820, 830},
    47: {15},
}

# ISO standards relevant to medical devices and quality management
_KNOWN_ISO: set[int] = {9001, 13485, 14971, 27001, 62304, 62366, 10993, 15223, 11135, 11607}

# IEC standards relevant to medical devices and software
_KNOWN_IEC: set[int] = {60601, 62304, 62366, 61010, 62133}

# EU regulation short codes
_KNOWN_EU_REGS: set[str] = {"2017/745", "2017/746", "2016/679", "2017/1369"}

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Matches: "21 CFR 820.30", "21 CFR Part 820", "21 CFR §820.30"
_CFR_RE = re.compile(
    r"\b(\d{1,3})\s+C\.?F\.?R\.?\s+(?:Part\s+|§\s*)?(\d+)(?:\.(\d+))?\b",
    re.IGNORECASE,
)

# Matches: "ISO 13485", "ISO 13485:2016", "ISO 13485:2016 §8.3"
_ISO_RE = re.compile(
    r"\bISO\s+(\d{4,5})(?::(\d{4}))?(?:\s+§[\d.]+)?\b",
    re.IGNORECASE,
)

# Matches: "IEC 62304", "IEC 62304:2006", "IEC 62304 Ed. 2"
_IEC_RE = re.compile(
    r"\bIEC\s+(\d{4,5})(?::(\d{4}))?(?:\s+Ed\.?\s*\d+)?\b",
    re.IGNORECASE,
)

# Matches: "EU MDR 2017/745", "EU IVDR 2017/746", "EU Regulation 2017/745"
_EU_MDR_RE = re.compile(
    r"\bEU\s+(?:MDR|IVDR|Regulation|Reg\.?)\s+(\d{4}/\d+)\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------


@dataclass
class CitationResult:
    """Result of a single citation check."""

    citation: str
    """The citation text as found in the document."""
    valid_format: bool
    """True if the citation matches a recognised format pattern."""
    known: bool
    """True if the cited standard/regulation appears in the known catalog."""
    issues: list[str] = field(default_factory=list)
    """Human-readable issue descriptions (empty list means no problems found)."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check_regulatory_citations(text: str) -> list[CitationResult]:
    """Extract and validate all regulatory citations found in ``text``.

    Returns one :class:`CitationResult` per citation occurrence.  Overlapping
    matches (e.g., the same citation appearing twice) each produce a separate
    result.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    results: list[CitationResult] = []

    for m in _CFR_RE.finditer(text):
        title = int(m.group(1))
        part = int(m.group(2))
        issues: list[str] = []

        known_titles = _KNOWN_CFR
        known_parts = known_titles.get(title, set())
        if title not in known_titles:
            issues.append(
                f"Title {title} CFR is not in the known catalog "
                f"(common titles: {sorted(known_titles.keys())})"
            )
        elif part not in known_parts:
            issues.append(
                f"21 CFR Part {part} is not in the known catalog "
                f"(known parts for Title {title}: {sorted(known_parts)})"
            )

        results.append(
            CitationResult(
                citation=m.group(0).strip(),
                valid_format=True,
                known=title in known_titles and part in _KNOWN_CFR.get(title, set()),
                issues=issues,
            )
        )

    for m in _ISO_RE.finditer(text):
        std_num = int(m.group(1))
        known = std_num in _KNOWN_ISO
        issues = (
            []
            if known
            else [
                f"ISO {std_num} is not in the known catalog "
                f"(known standards: {sorted(_KNOWN_ISO)})"
            ]
        )
        results.append(
            CitationResult(
                citation=m.group(0).strip(),
                valid_format=True,
                known=known,
                issues=issues,
            )
        )

    for m in _IEC_RE.finditer(text):
        std_num = int(m.group(1))
        known = std_num in _KNOWN_IEC
        issues = (
            []
            if known
            else [
                f"IEC {std_num} is not in the known catalog "
                f"(known standards: {sorted(_KNOWN_IEC)})"
            ]
        )
        results.append(
            CitationResult(
                citation=m.group(0).strip(),
                valid_format=True,
                known=known,
                issues=issues,
            )
        )

    for m in _EU_MDR_RE.finditer(text):
        reg_num = m.group(1)
        known = reg_num in _KNOWN_EU_REGS
        issues = (
            []
            if known
            else [
                f"EU Regulation {reg_num} is not in the known catalog "
                f"(known: {sorted(_KNOWN_EU_REGS)})"
            ]
        )
        results.append(
            CitationResult(
                citation=m.group(0).strip(),
                valid_format=True,
                known=known,
                issues=issues,
            )
        )

    return results

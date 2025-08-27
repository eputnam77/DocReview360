"""Simple heading numbering utilities (Task 101 and 104)."""

from __future__ import annotations

from typing import Mapping


def apply_numbering(text: str, mapping: Mapping[str, str]) -> str:
    """Return ``text`` with headings numbered using ``mapping``.

    Parameters
    ----------
    text:
        Markdown content to process.
    mapping:
        Mapping of heading title to numbering prefix.
    """
    lines = []
    for line in text.splitlines():
        if line.startswith("#"):
            # Preserve the heading level instead of unconditionally
            # replacing it with a single ``#``.  The previous
            # implementation collapsed all headings to level 1, e.g.
            # ``## Section`` became ``# ...`` after numbering which
            # lost structural information.  Determine the number of ``#``
            # characters and rebuild the line accordingly.
            level = len(line) - len(line.lstrip("#"))
            heading = line[level:].strip()
            if heading in mapping:
                prefix = mapping[heading]
                line = f"{'#' * level} {prefix} {heading}"
        lines.append(line)
    return "\n".join(lines)


def can_toggle_numbering(role: str, rbac: Mapping[str, Mapping[str, bool] | None]) -> bool:
    """Return ``True`` if ``role`` may toggle numbering."""
    perms = rbac.get(role) or {}
    if not isinstance(perms, Mapping):
        return False
    return perms.get("toggle_numbering", False)

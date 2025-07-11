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
            heading = line.lstrip("# ")
            if heading in mapping:
                prefix = mapping[heading]
                line = f"# {prefix} {heading}"
        lines.append(line)
    return "\n".join(lines)


def can_toggle_numbering(role: str, rbac: Mapping[str, Mapping[str, bool]]) -> bool:
    """Return ``True`` if ``role`` may toggle numbering."""
    perms = rbac.get(role, {})
    return perms.get("toggle_numbering", False)

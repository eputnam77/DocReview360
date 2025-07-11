"""Contextual help and tutorial registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class HelpItem:
    """Single help entry."""

    text: str
    video: Optional[str] = None


_HELP: Dict[str, HelpItem] = {}


def register_help(topic: str, text: str, video: str | None = None) -> None:
    """Register a help snippet for ``topic`` with optional video."""
    if not topic or not text:
        raise ValueError("topic and text required")
    _HELP[topic] = HelpItem(text=text, video=video)


def get_help(topic: str) -> HelpItem | None:
    """Return help item for ``topic`` or ``None``."""
    return _HELP.get(topic)


def tooltip_html(topic: str) -> str:
    """Return HTML snippet for the help tooltip."""
    item = get_help(topic)
    if not item:
        return ""
    tooltip = f'<span class="tooltip" data-tip="{item.text}">?</span>'
    if item.video:
        tooltip += f'<iframe src="{item.video}" frameborder="0" class="help-video"></iframe>'
    return tooltip

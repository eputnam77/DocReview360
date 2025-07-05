"""Contextual help and tutorial registry."""

from __future__ import annotations

from typing import Dict

_HELP: Dict[str, str] = {}


def register_help(topic: str, text: str) -> None:
    """Register a help snippet for ``topic``."""
    if not topic:
        raise ValueError("topic required")
    _HELP[topic] = text


def get_help(topic: str) -> str:
    """Return help text for ``topic`` or a default message."""
    return _HELP.get(topic, "No help available")

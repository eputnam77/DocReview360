"""User profile preference helpers."""

from __future__ import annotations

from typing import Any, Dict, cast

from .settings_manager import load_settings, update_setting

VALID_THEMES = {"system", "light", "dark"}
"""Allowed theme values for appearance preferences."""


def get_preferences(user: str) -> Dict[str, Any]:
    """Return stored preferences for ``user``.

    Parameters
    ----------
    user:
        Username to load preferences for.
    """
    settings = load_settings()
    stored = settings.get(f"prefs_{user}", {})
    return cast(Dict[str, Any], stored)


def update_preferences(user: str, prefs: Dict[str, Any]) -> Dict[str, Any]:
    """Update ``user`` preferences and persist them.

    Parameters
    ----------
    user:
        Username owning the preferences.
    prefs:
        Mapping of preference keys to values.
    """
    current = get_preferences(user)
    cleaned: Dict[str, Any] = {}
    for key, val in prefs.items():
        if key == "theme":
            if isinstance(val, str) and val.lower() in VALID_THEMES:
                cleaned[key] = val.lower()
        elif key == "reduce_motion":
            if isinstance(val, str):
                cleaned[key] = val.strip().lower() in {"1", "true", "yes", "on"}
            else:
                cleaned[key] = bool(val)
    current.update(cleaned)
    update_setting(f"prefs_{user}", current)
    return current

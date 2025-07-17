"""User profile preference helpers."""

from __future__ import annotations

from typing import Any, Dict, cast

from .settings_manager import load_settings, update_setting


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
    current.update({k: bool(v) for k, v in prefs.items()})
    update_setting(f"prefs_{user}", current)
    return current

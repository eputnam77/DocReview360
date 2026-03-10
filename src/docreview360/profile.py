# SPDX-License-Identifier: MIT
"""User profile preference helpers."""

from __future__ import annotations

from typing import Any, Dict, cast

from .settings_manager import load_settings, update_setting

VALID_THEMES = {"system", "light", "dark"}
"""Allowed theme values for appearance preferences."""

PROFILE_DEFAULTS: Dict[str, Any] = {
    "picture": "",
    "displayName": "",
    "email": "",
    "phone": "",
    "shorthand": "",
    "jobTitle": "",
    "department": "",
    "timeZone": "America/New_York",
    "dashboards": ["main"],
    "permissions": ["user"],
    "notificationEmail": True,
    "notificationSMS": False,
    "twoFA": False,
}

PROFILE_STRING_FIELDS = {
    "picture",
    "displayName",
    "email",
    "phone",
    "shorthand",
    "jobTitle",
    "department",
    "timeZone",
}
PROFILE_LIST_FIELDS = {"dashboards", "permissions"}
PROFILE_BOOL_FIELDS = {"notificationEmail", "notificationSMS", "twoFA"}


def get_profile_data(user: str) -> Dict[str, Any]:
    """Return stored profile data for ``user`` with defaults applied."""
    settings = load_settings()
    stored = settings.get(f"profile_{user}", {})
    if not isinstance(stored, dict):
        stored = {}
    profile: Dict[str, Any] = dict(PROFILE_DEFAULTS)
    for key, val in stored.items():
        if key in PROFILE_STRING_FIELDS and isinstance(val, str):
            profile[key] = val
        elif key in PROFILE_LIST_FIELDS and isinstance(val, list):
            profile[key] = [str(v).strip() for v in val if str(v).strip()]
        elif key in PROFILE_BOOL_FIELDS:
            profile[key] = bool(val)
    return profile


def update_profile_data(user: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update ``user`` profile fields and persist them."""
    if not isinstance(updates, dict):
        raise TypeError("updates must be a mapping")
    current = get_profile_data(user)
    cleaned: Dict[str, Any] = {}
    for key, val in updates.items():
        if val is None:
            continue
        if key in PROFILE_STRING_FIELDS and isinstance(val, str):
            cleaned[key] = val
        elif key in PROFILE_LIST_FIELDS and isinstance(val, list):
            cleaned[key] = [str(v).strip() for v in val if str(v).strip()]
        elif key in PROFILE_BOOL_FIELDS:
            cleaned[key] = bool(val)
    current.update(cleaned)
    update_setting(f"profile_{user}", current)
    return current


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
    if not isinstance(prefs, dict):
        raise TypeError("prefs must be a mapping")
    current = get_preferences(user)
    cleaned: Dict[str, Any] = {}
    for key, val in prefs.items():
        if key == "theme":
            if isinstance(val, str):
                normalized = val.strip().lower()
                if normalized in VALID_THEMES:
                    cleaned[key] = normalized
        elif key == "reduce_motion":
            if isinstance(val, str):
                cleaned[key] = val.strip().lower() in {"1", "true", "yes", "on"}
            else:
                cleaned[key] = bool(val)
    current.update(cleaned)
    update_setting(f"prefs_{user}", current)
    return current

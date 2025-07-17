"""Dashboard widget visibility helpers."""

from __future__ import annotations

from typing import Any, Dict

from .settings_manager import load_settings, update_setting

DEFAULT_VISIBILITY: Dict[str, bool] = {
    "stats": True,
    "status": True,
    "activity": True,
    "logs": True,
}


def get_visibility(user: str) -> Dict[str, bool]:
    """Return widget visibility settings for ``user``."""
    data = load_settings()
    stored = data.get(f"dash_{user}", {})
    return {**DEFAULT_VISIBILITY, **stored}


def set_visibility(user: str, visibility: Dict[str, Any]) -> Dict[str, bool]:
    """Persist visibility settings for ``user``."""
    current = get_visibility(user)
    current.update({k: bool(v) for k, v in visibility.items()})
    update_setting(f"dash_{user}", current)
    return current

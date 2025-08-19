"""Project-level editor preference helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from pydantic import BaseModel

from .settings_manager import SETTINGS_FILE, load_settings, update_setting


class ProjectPreferences(BaseModel):
    """Editor extension toggles scoped to a project."""

    lint: bool = False
    collab: bool = False
    ai_suggest: bool = False
    heading_lock: bool = False
    indentation: bool = False
    section_node: bool = False
    mark_review: bool = False
    watermark: bool = False
    watermark_text: str = "Sample"


def _key(project_id: str) -> str:
    return f"projectprefs_{project_id}"


def get_project_preferences(project_id: str, *, path: Path | None = None) -> ProjectPreferences:
    """Return stored preferences for ``project_id``."""
    settings = load_settings(path or SETTINGS_FILE)
    stored = settings.get(_key(project_id), {})
    return ProjectPreferences(**stored)


def update_project_preferences(
    project_id: str, prefs: Dict[str, Any], *, path: Path | None = None
) -> ProjectPreferences:
    """Update ``project_id`` preferences and persist them."""
    current = get_project_preferences(project_id, path=path)
    updates: Dict[str, Any] = {}
    for key, val in prefs.items():
        # Access model_fields on the class to avoid Pydantic deprecation
        if key in ProjectPreferences.model_fields:
            if isinstance(getattr(current, key), bool):
                updates[key] = bool(val)
            elif key == "watermark_text" and isinstance(val, str):
                updates[key] = val
    updated = current.model_copy(update=updates)
    update_setting(_key(project_id), updated.model_dump(), path or SETTINGS_FILE)
    return updated

"""Global settings persistence (Task 142)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

from .stubs import record_task_completion

SETTINGS_FILE = Path("settings.yaml")


def load_settings(path: Path = SETTINGS_FILE) -> Dict[str, Any]:
    """Return settings from ``path`` or an empty mapping."""
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {path}") from exc


def update_setting(key: str, value: Any, path: Path = SETTINGS_FILE) -> None:
    """Update a single setting and persist to ``path``."""
    settings = load_settings(path)
    settings[key] = value
    path.write_text(yaml.safe_dump(settings))
    record_task_completion(142)

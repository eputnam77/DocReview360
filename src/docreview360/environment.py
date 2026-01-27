"""Environment switching utilities (Task 147)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

import yaml

from .stubs import record_task_completion

ENV_FILE = Path("environments.yaml")


def load_envs(path: Path | None = None) -> Dict[str, Dict[str, str]]:
    """Return configured environments."""
    path = path or ENV_FILE
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {path}") from exc
    if not isinstance(data, dict):
        raise ValueError("Environment configuration must be a mapping")
    return data


def add_environment(name: str, url: str, color: str, path: Path | None = None) -> None:
    """Persist a new environment record."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name required")
    if not isinstance(url, str) or not url.strip():
        raise ValueError("url required")
    if not isinstance(color, str) or not color.strip():
        raise ValueError("color required")
    path = path or ENV_FILE
    data = load_envs(path)
    data[name.strip()] = {"url": url.strip(), "color": color.strip()}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data))


def switch_environment(name: str, path: Path | None = None) -> str:
    """Switch current environment and return its URL."""
    path = path or ENV_FILE
    data = load_envs(path)
    if not isinstance(name, str):
        raise TypeError("name must be a string")
    normalized = name.strip()
    if not normalized:
        raise ValueError("name required")
    if normalized not in data:
        raise KeyError(name)
    os.environ["DOCREVIEW360_ENV"] = normalized
    record_task_completion(147)
    return data[normalized]["url"]


def current_environment(path: Path | None = None) -> Optional[Dict[str, str]]:
    """Return the currently selected environment record."""
    path = path or ENV_FILE
    env = os.environ.get("DOCREVIEW360_ENV")
    if not env:
        return None
    normalized = env.strip()
    if not normalized:
        return None
    return load_envs(path).get(normalized)

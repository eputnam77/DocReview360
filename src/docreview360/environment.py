# SPDX-License-Identifier: MIT
"""Environment switching utilities (Task 147)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

import yaml

from .yaml_loader import load_yaml_file, save_yaml_file

ENV_FILE = Path(os.getenv("DOCREVIEW360_ENVIRONMENTS_FILE", "environments.yaml"))


def load_envs(path: Path | None = None) -> Dict[str, Dict[str, str]]:
    """Return configured environments."""
    path = path or ENV_FILE
    if not path.exists():
        return {}
    data = load_yaml_file(path, default={}) or {}
    if not isinstance(data, dict):
        raise ValueError("Environment configuration must be a mapping")
    validated: Dict[str, Dict[str, str]] = {}
    for name, payload in data.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Environment names must be non-empty strings")
        if not isinstance(payload, dict):
            raise ValueError("Environment entries must be mappings")
        url = payload.get("url")
        color = payload.get("color")
        if not isinstance(url, str) or not url.strip():
            raise ValueError("Environment url must be a non-empty string")
        if not isinstance(color, str) or not color.strip():
            raise ValueError("Environment color must be a non-empty string")
        validated[name.strip()] = {"url": url.strip(), "color": color.strip()}
    return validated


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
    save_yaml_file(path, data)


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

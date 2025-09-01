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
    path = path or ENV_FILE
    data = load_envs(path)
    data[name] = {"url": url, "color": color}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data))


def switch_environment(name: str, path: Path | None = None) -> str:
    """Switch current environment and return its URL."""
    path = path or ENV_FILE
    data = load_envs(path)
    if name not in data:
        raise KeyError(name)
    os.environ["DOCREVIEW360_ENV"] = name
    record_task_completion(147)
    return data[name]["url"]


def current_environment(path: Path | None = None) -> Optional[Dict[str, str]]:
    """Return the currently selected environment record."""
    path = path or ENV_FILE
    env = os.environ.get("DOCREVIEW360_ENV")
    if not env:
        return None
    return load_envs(path).get(env)

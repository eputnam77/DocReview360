"""Environment switching utilities (Task 147)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

import yaml

from .stubs import record_task_completion

ENV_FILE = Path("environments.yaml")


def load_envs(path: Path = ENV_FILE) -> Dict[str, Dict[str, str]]:
    """Return configured environments."""
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def add_environment(name: str, url: str, color: str, path: Path = ENV_FILE) -> None:
    """Persist a new environment record."""
    data = load_envs(path)
    data[name] = {"url": url, "color": color}
    path.write_text(yaml.safe_dump(data))


def switch_environment(name: str, path: Path = ENV_FILE) -> str:
    """Switch current environment and return its URL."""
    data = load_envs(path)
    if name not in data:
        raise KeyError(name)
    os.environ["DOCUFLOW_ENV"] = name
    record_task_completion(147)
    return data[name]["url"]

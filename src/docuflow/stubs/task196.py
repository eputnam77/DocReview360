"""Implementation for task 196."""

import tomllib
from pathlib import Path
from typing import Any, Dict

from ..stubs import record_task_completion


def task196() -> str:
    """Return the project description from ``pyproject.toml``."""
    record_task_completion(196)
    path = Path(__file__).resolve().parents[3] / "pyproject.toml"
    data: Dict[str, Any] = tomllib.loads(path.read_text())
    return str(data["project"]["description"])

"""Simplified plugin installer and marketplace utilities."""

from __future__ import annotations

import subprocess
import sys

from .stubs import record_task_completion

# Hard-coded demo packages exposed via the marketplace API.
AVAILABLE_PLUGINS = ["grammar-plugin", "demo-extension"]


def list_available() -> list[str]:
    """Return the list of installable packages."""
    return AVAILABLE_PLUGINS.copy()


def install_plugin(name: str) -> None:
    """Install a plugin via ``pip``."""
    if not name:
        raise ValueError("name is required")
    subprocess.check_call([sys.executable, "-m", "pip", "install", name])
    record_task_completion(145)

"""Simplified plugin installation helper (Task 145)."""

from __future__ import annotations

import subprocess
import sys

from .stubs import record_task_completion


def install_plugin(name: str) -> None:
    """Install a plugin via ``pip``."""
    if not name:
        raise ValueError("name is required")
    subprocess.check_call([sys.executable, "-m", "pip", "install", name])
    record_task_completion(145)

"""Helm smoke test helper."""

import subprocess
from pathlib import Path

from . import record_task_completion


async def task137() -> None:
    """Execute the Helm smoke test."""
    script = Path("scripts/helm_smoke.py")
    subprocess.run(["python", str(script)], check=True)
    record_task_completion(137)

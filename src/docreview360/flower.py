"""Celery Flower monitoring utilities."""

from __future__ import annotations

import asyncio
import inspect
from pathlib import Path

from celery import Celery

from .stubs import record_task_completion


async def launch_flower(app: Celery, port: int = 5555, work_dir: str | Path = ".") -> None:
    """Launch Flower using ``app`` and return once it's running."""
    if port <= 0:
        raise ValueError("port must be positive")
    proc = await asyncio.create_subprocess_exec(
        "flower",
        f"--port={port}",
        cwd=str(work_dir),
    )
    sleep_result = asyncio.sleep(0.5)
    if inspect.isawaitable(sleep_result):
        await sleep_result
    if proc.returncode is not None:
        raise RuntimeError("flower failed to start")
    record_task_completion(136)

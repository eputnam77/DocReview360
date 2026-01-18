import asyncio
import contextlib
from datetime import timedelta

import pytest

from docreview360.secrets import schedule_rotation


@pytest.mark.asyncio
async def test_schedule_rotation_rejects_non_positive_interval() -> None:
    """Negative intervals should raise immediately rather than spawning a task."""

    def loader() -> str:
        return "secret"

    task: asyncio.Task | None = None
    with pytest.raises(ValueError):
        task = schedule_rotation("provider", loader, timedelta(seconds=-1))
    if task is not None:
        task.cancel()
        with contextlib.suppress(Exception):
            await task

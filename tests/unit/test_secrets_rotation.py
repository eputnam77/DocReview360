import asyncio
import types
from datetime import timedelta

from docreview360 import secrets


def test_schedule_rotation_uses_asyncio_create_task(monkeypatch):
    called = {}

    async def dummy_rotate(provider, loader, interval):
        return None

    vault = secrets._vault
    monkeypatch.setattr(vault, "rotate", dummy_rotate)

    def fake_create_task(coro):
        called["called"] = isinstance(coro, types.CoroutineType)
        # Consume the coroutine to avoid "never awaited" warnings and return a
        # simple sentinel object standing in for the scheduled task. Using a
        # plain object avoids event loop warnings from creating real Future
        # instances without a running loop.
        coro.close()
        return object()

    monkeypatch.setattr(asyncio, "create_task", fake_create_task)
    sentinel = secrets.schedule_rotation("p", lambda: "s", timedelta(seconds=1))
    assert called.get("called")
    assert sentinel is not None

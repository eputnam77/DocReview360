import asyncio
import types
import pytest
from datetime import timedelta
from docreview360 import secrets


def test_schedule_rotation_uses_asyncio_create_task(monkeypatch):
    called = {}
    async def dummy_rotate(provider, loader, interval):
        pass
    vault = secrets._vault
    monkeypatch.setattr(vault, "rotate", dummy_rotate)
    def fake_create_task(coro):
        called['called'] = isinstance(coro, types.CoroutineType)
    monkeypatch.setattr(asyncio, "create_task", fake_create_task)
    secrets.schedule_rotation("p", lambda: "s", timedelta(seconds=1))
    assert called.get('called')

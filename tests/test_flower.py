from __future__ import annotations

from typing import Any, cast

import pytest
from celery import Celery
from docreview360 import flower


@pytest.mark.asyncio
async def test_launch_flower_success(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyProc:
        returncode = None

    async def fake_create(*args: object, **kwargs: object) -> DummyProc:
        return DummyProc()

    async_mod = cast(Any, getattr(flower, "asyncio"))
    monkeypatch.setattr(async_mod, "create_subprocess_exec", fake_create)
    monkeypatch.setattr(async_mod, "sleep", lambda t: None)
    calls = []
    monkeypatch.setattr(flower, "record_task_completion", lambda x: calls.append(x))

    await flower.launch_flower(Celery("doc"), port=1234, work_dir=".")
    assert calls == [136]


@pytest.mark.asyncio
async def test_launch_flower_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyProc:
        returncode = 1

    async def fake_create(*args: object, **kwargs: object) -> DummyProc:
        return DummyProc()

    async_mod = cast(Any, getattr(flower, "asyncio"))
    monkeypatch.setattr(async_mod, "create_subprocess_exec", fake_create)
    monkeypatch.setattr(async_mod, "sleep", lambda t: None)

    with pytest.raises(RuntimeError):
        await flower.launch_flower(Celery("doc"))


@pytest.mark.asyncio
async def test_launch_flower_bad_port() -> None:
    with pytest.raises(ValueError):
        await flower.launch_flower(Celery("doc"), port=0)

import pytest
from celery import Celery

from docuflow import flower


@pytest.mark.asyncio
async def test_launch_flower_success(monkeypatch):
    class DummyProc:
        returncode = None

    async def fake_create(*args, **kwargs):
        return DummyProc()

    monkeypatch.setattr(flower.asyncio, "create_subprocess_exec", fake_create)
    monkeypatch.setattr(flower.asyncio, "sleep", lambda t: None)
    calls = []
    monkeypatch.setattr(flower, "record_task_completion", lambda x: calls.append(x))

    await flower.launch_flower(Celery("doc"), port=1234, work_dir=".")
    assert calls == [136]


@pytest.mark.asyncio
async def test_launch_flower_failure(monkeypatch):
    class DummyProc:
        returncode = 1

    async def fake_create(*args, **kwargs):
        return DummyProc()

    monkeypatch.setattr(flower.asyncio, "create_subprocess_exec", fake_create)
    monkeypatch.setattr(flower.asyncio, "sleep", lambda t: None)

    with pytest.raises(RuntimeError):
        await flower.launch_flower(Celery("doc"))


@pytest.mark.asyncio
async def test_launch_flower_bad_port():
    with pytest.raises(ValueError):
        await flower.launch_flower(Celery("doc"), port=0)

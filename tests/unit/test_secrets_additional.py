import asyncio
import types
from datetime import datetime, timedelta

import pytest

import docreview360.secrets as secrets
from docreview360.secrets import configure_vault, get_secret, schedule_rotation, store_secret


def test_store_negative_ttl_raises():
    with pytest.raises(ValueError):
        store_secret("prov", "sec", ttl=timedelta(seconds=-5))


def test_store_get_and_expiry(monkeypatch: pytest.MonkeyPatch):
    secrets._vault._secrets.clear()
    store_secret("p1", "secret", ttl=timedelta(seconds=1))
    assert get_secret("p1") == "secret"
    # simulate time after expiry
    future = datetime.utcnow() + timedelta(seconds=2)
    monkeypatch.setattr(secrets, "datetime", types.SimpleNamespace(utcnow=lambda: future))
    # Expired secrets should now return ``None`` allowing callers to fall back
    # to other sources without needing to catch an exception.
    assert get_secret("p1") is None


def test_env_fallback(monkeypatch: pytest.MonkeyPatch):
    secrets._vault._secrets.clear()
    monkeypatch.setenv("P2_TOKEN", "env")
    assert get_secret("p2") == "env"


def test_blank_provider_rejected():
    with pytest.raises(ValueError):
        store_secret("   ", "x")
    with pytest.raises(ValueError):
        get_secret("")


def test_schedule_rotation_and_configure(monkeypatch: pytest.MonkeyPatch):
    called = {}

    def fake_store(provider, value, ttl=None):
        called["store"] = (provider, value)
        raise asyncio.CancelledError

    async def fake_sleep(seconds):
        return None

    monkeypatch.setattr(secrets._vault, "store", fake_store)
    monkeypatch.setattr(secrets.asyncio, "sleep", fake_sleep)

    task_called = {}

    def fake_create_task(coro):
        task_called["task"] = True
        coro.close()

    monkeypatch.setattr(secrets.asyncio, "create_task", fake_create_task)

    configure_vault({"url": "u", "token": "t"})
    assert secrets._vault.url == "u" and secrets._vault.token == "t"

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(secrets._vault.rotate("p", lambda: "v", timedelta(seconds=1)))

    schedule_rotation("p", lambda: "v", timedelta(seconds=1))
    assert task_called["task"]

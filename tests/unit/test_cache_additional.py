import importlib
import sys
import types

import pytest

from docreview360 import cache


class DummyRedis:
    def __init__(self) -> None:
        self.store: dict[str, tuple[str, int | None]] = {}

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.store[key] = (value, ex)

    def get(self, key: str) -> str | None:
        return self.store.get(key, (None, None))[0]

    def flushdb(self) -> None:  # pragma: no cover - simple
        self.store.clear()

    def ping(self) -> None:  # pragma: no cover - simple
        pass


def test_cache_negative_ttl_raises() -> None:
    with pytest.raises(ValueError):
        cache.cache_set("k", "v", ttl=-1)


def test_cache_remote_client(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy = DummyRedis()
    monkeypatch.setattr(cache, "_redis", types.SimpleNamespace(Redis=lambda *a, **k: dummy))
    cache._client = None
    cache.cache_set("a", "b", ttl=1)
    assert cache.cache_get("a") == "b"
    cache.clear_cache()
    assert dummy.store == {}


def test_cache_fallback_expiry(monkeypatch: pytest.MonkeyPatch) -> None:
    cache._client = None
    monkeypatch.setattr(cache, "_redis", None)
    cache.clear_cache()
    fake_time = [0.0]
    monkeypatch.setattr(cache.time, "monotonic", lambda: fake_time[0])
    cache.cache_set("a", "b", ttl=1)
    fake_time[0] = 2.0
    assert cache.cache_get("a") is None


def test_cache_import_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "redis", None)
    import docreview360.cache as c

    importlib.reload(c)
    assert c._redis is None
    # restore original module for subsequent tests
    sys.modules.pop("docreview360.cache", None)
    import docreview360.cache  # noqa: F401

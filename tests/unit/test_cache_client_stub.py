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

    def delete(self, key: str) -> None:  # pragma: no cover - trivial
        self.store.pop(key, None)

    def flushdb(self) -> None:  # pragma: no cover - trivial
        self.store.clear()

    def ping(self) -> None:  # pragma: no cover - trivial
        pass


def test_cache_uses_stub_without_from_url(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy = DummyRedis()
    monkeypatch.setattr(cache, "_redis", types.SimpleNamespace(Redis=lambda url: dummy))
    cache._client = None
    cache.clear_cache()
    cache.cache_set("a", "b")
    assert dummy.store["a"][0] == "b"
    cache.clear_cache()
    cache._client = None

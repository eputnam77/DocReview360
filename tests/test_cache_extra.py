from __future__ import annotations

import pytest
from docreview360 import cache


class BrokenClient:
    def set(self, *a, **kw):
        pass

    def get(self, key):  # pragma: no cover - not used
        return None

    def delete(self, key):
        raise RuntimeError("boom")

    def flushdb(self):
        raise RuntimeError("boom")


def test_cache_error_paths(monkeypatch) -> None:
    # Trigger AttributeError in _get_client when Redis lacks Redis attr
    cache._client = None
    monkeypatch.setattr(cache, "_redis", object())
    assert cache._get_client() is None

    # Now supply a broken client to exercise delete/flushdb exception handling
    monkeypatch.setattr(cache, "_client", BrokenClient())
    cache.cache_set("k", "v")
    cache.cache_delete("k")  # delete error swallowed
    cache.clear_cache()  # flushdb error swallowed

    # Fallback to local cache for TTL logic
    monkeypatch.setattr(cache, "_client", None)
    monkeypatch.setattr(cache, "_redis", None)
    with pytest.raises(ValueError):
        cache.cache_set("x", "v", ttl=-5)
    cache.cache_set("y", "v", ttl=0)
    assert cache.cache_get("y") == "v"

from docreview360 import cache


def test_clear_cache_handles_redis_error(monkeypatch):
    class BadClient:
        def flushdb(self):
            raise RuntimeError("boom")

    # ensure fallback has an item
    cache._cache["x"] = ("y", None)
    # monkeypatch redis client
    monkeypatch.setattr(cache, "_client", BadClient())
    # should not raise and should clear local cache
    cache.clear_cache()
    assert cache._cache == {}
    monkeypatch.setattr(cache, "_client", None)

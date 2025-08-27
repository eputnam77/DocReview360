import time

from docreview360.cache import cache_get, cache_set, clear_cache


def setup_function(_):
    clear_cache()


def test_cache_ttl_behaviour():
    cache_set("a", 1, ttl=0)
    assert cache_get("a") == 1
    cache_set("b", 2, ttl=1)
    assert cache_get("b") == 2
    time.sleep(1.1)
    assert cache_get("b") is None


def test_cache_negative_ttl():
    try:
        cache_set("c", 3, ttl=-1)
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("negative ttl should raise")

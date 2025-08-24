from docreview360 import cache


def test_cache_ttl_expiration_immediate():
    cache.clear_cache()
    cache.cache_set('key', 'value', ttl=0)
    assert cache.cache_get('key') is None

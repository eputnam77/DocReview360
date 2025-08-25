from docreview360 import cache


def test_cache_ttl_zero_persists():
    cache.clear_cache()
    cache.cache_set('key', 'value', ttl=0)
    assert cache.cache_get('key') == 'value'

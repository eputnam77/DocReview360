from hypothesis import given
from hypothesis import strategies as st

from docreview360.cache import cache_get, cache_set, clear_cache


@given(st.text())
def test_cache_roundtrip(value: str) -> None:
    clear_cache()
    cache_set("k", value)
    assert cache_get("k") == value

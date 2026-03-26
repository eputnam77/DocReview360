import pytest
from docreview360.cache import cache_set


def test_cache_set_rejects_non_numeric_ttl():
    with pytest.raises(TypeError) as excinfo:
        cache_set("k", "v", ttl="5")
    assert "ttl must be int or float" in str(excinfo.value)


def test_cache_set_rejects_boolean_ttl() -> None:
    """Booleans are instances of :class:`int` and previously slipped through
    the numeric type check which meant ``True`` was interpreted as a TTL of
    ``1``.  Cache callers should provide an explicit numeric value so a boolean
    input should raise ``TypeError``."""
    with pytest.raises(TypeError) as excinfo:
        cache_set("k", "v", ttl=True)
    assert "ttl must be int or float" in str(excinfo.value)

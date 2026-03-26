import math

import pytest
from docreview360.cache import cache_set


def test_cache_set_rejects_negative_ttl():
    with pytest.raises(ValueError):
        cache_set("k", "v", ttl=-1)


def test_cache_set_rejects_nonfinite_ttl():
    with pytest.raises(ValueError):
        cache_set("k", "v", ttl=math.nan)
    with pytest.raises(ValueError):
        cache_set("k", "v", ttl=math.inf)

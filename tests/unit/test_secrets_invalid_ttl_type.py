import pytest
from docreview360 import secrets


def test_store_secret_invalid_ttl_type():
    with pytest.raises(TypeError, match="ttl must be a datetime.timedelta"):
        secrets.store_secret("svc", "token", ttl="not-a-timedelta")

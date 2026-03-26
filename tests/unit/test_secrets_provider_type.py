import pytest
from docreview360.secrets import get_secret, store_secret


def test_store_secret_non_string_provider():
    with pytest.raises(TypeError):
        store_secret(123, "secret")


def test_get_secret_non_string_provider():
    with pytest.raises(TypeError):
        get_secret(456)

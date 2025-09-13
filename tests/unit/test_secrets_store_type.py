import pytest

from docreview360 import secrets


def test_store_secret_rejects_non_string() -> None:
    with pytest.raises(TypeError):
        secrets.store_secret("svc", 123)  # type: ignore[arg-type]

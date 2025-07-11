import pytest

from docreview360.stubs.task76 import authenticate_keycloak, has_role


def test_authenticate_success() -> None:
    token = authenticate_keycloak("admin", "secret", "123456")
    assert isinstance(token, str)
    assert has_role(token, "admin")


def test_authenticate_failure() -> None:
    with pytest.raises(ValueError):
        authenticate_keycloak("admin", "wrong", "000")

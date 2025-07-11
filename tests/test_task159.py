import pytest

from docreview360.auth import keycloak_mfa_login


def test_keycloak_mfa_login_success() -> None:
    token = keycloak_mfa_login("admin", "secret", "123456")
    assert isinstance(token, str)


def test_keycloak_mfa_login_failure() -> None:
    with pytest.raises(ValueError):
        keycloak_mfa_login("admin", "wrong", "000")

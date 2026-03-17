from jose import jwt
import pytest
from fastapi import HTTPException

from docreview360 import auth
from docreview360.auth import USER_REPOSITORY, create_id_token, get_current_user_oidc


class DummyRequest:
    def __init__(self, cookies=None, headers=None):
        self.cookies = cookies or {}
        self.headers = headers or {}


def test_get_current_user_oidc_rejects_inactive_user() -> None:
    USER_REPOSITORY.set_active("bob", False)
    token = create_id_token({"sub": "bob"})
    request = DummyRequest()
    with pytest.raises(HTTPException):
        get_current_user_oidc(request, token)
    USER_REPOSITORY.set_active("bob", True)


def test_get_current_user_oidc_accepts_previous_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth, "OIDC_SECRET_KEY", "oidc-current-secret")
    monkeypatch.setattr(auth, "OIDC_SECRET_KEY_PREVIOUS", "oidc-previous-secret")

    if USER_REPOSITORY.get_user("alice") is None:
        USER_REPOSITORY._seed_user("alice", "password", otp_secret="123456", active=True)

    token = jwt.encode(
        {"sub": "alice", "iss": auth.OIDC_TOKEN_ISSUER, "aud": auth.OIDC_TOKEN_AUDIENCE},
        "oidc-previous-secret",
        algorithm=auth.OIDC_ALGORITHM,
    )

    user = get_current_user_oidc(DummyRequest(), token)
    assert user.username == "alice"


def test_get_current_user_oidc_rejects_invalid_when_no_previous(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(auth, "OIDC_SECRET_KEY", "oidc-current-secret")
    monkeypatch.setattr(auth, "OIDC_SECRET_KEY_PREVIOUS", None)

    token = jwt.encode(
        {"sub": "alice", "iss": auth.OIDC_TOKEN_ISSUER, "aud": auth.OIDC_TOKEN_AUDIENCE},
        "oidc-previous-secret",
        algorithm=auth.OIDC_ALGORITHM,
    )

    with pytest.raises(HTTPException, match="Invalid token"):
        get_current_user_oidc(DummyRequest(), token)

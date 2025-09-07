import pytest
from docreview360.auth import FAKE_USERS_DB, HTTPException, create_id_token, get_current_user_oidc


class DummyRequest:
    def __init__(self, cookies=None):
        self.cookies = cookies or {}


def test_get_current_user_oidc_rejects_inactive_user():
    # temporarily mark user inactive
    FAKE_USERS_DB["bob"]["active"] = False
    token = create_id_token({"sub": "bob"})
    request = DummyRequest()
    with pytest.raises(HTTPException):
        get_current_user_oidc(request, token)
    # restore state
    FAKE_USERS_DB["bob"]["active"] = True

import pytest
from fastapi import HTTPException

from docreview360.auth import USER_REPOSITORY, create_id_token, get_current_user_oidc


class DummyRequest:
    def __init__(self, cookies=None):
        self.cookies = cookies or {}


def test_get_current_user_oidc_rejects_inactive_user():
    # temporarily mark user inactive
    USER_REPOSITORY.set_active("bob", False)
    token = create_id_token({"sub": "bob"})
    request = DummyRequest()
    with pytest.raises(HTTPException):
        get_current_user_oidc(request, token)
    # restore state
    USER_REPOSITORY.set_active("bob", True)

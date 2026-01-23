import pytest
from jose import jwt

from docreview360.okta import verify_okta_token

SECRET = "secret"
ISSUER = "https://okta.example.com/"
AUDIENCE = "my-app"


def test_verify_okta_token() -> None:
    token = jwt.encode({"sub": "abc", "aud": AUDIENCE, "iss": ISSUER}, SECRET, algorithm="HS256")
    claims = verify_okta_token(token, SECRET, ISSUER, AUDIENCE)
    assert claims["sub"] == "abc"


def test_verify_okta_token_validation() -> None:
    token = jwt.encode({"sub": "abc", "aud": AUDIENCE, "iss": ISSUER}, SECRET, algorithm="HS256")
    with pytest.raises(TypeError):
        verify_okta_token(123, SECRET, ISSUER, AUDIENCE)
    with pytest.raises(ValueError):
        verify_okta_token("", SECRET, ISSUER, AUDIENCE)
    with pytest.raises(ValueError):
        verify_okta_token(token, "", ISSUER, AUDIENCE)
    with pytest.raises(ValueError):
        verify_okta_token(token, SECRET, "", AUDIENCE)
    with pytest.raises(ValueError):
        verify_okta_token(token, SECRET, ISSUER, "")

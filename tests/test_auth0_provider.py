import pytest
from docreview360.auth0_provider import verify_auth0_token
from jose import jwt

SECRET = "secret"
ISSUER = "https://auth.example.com/"
AUDIENCE = "my-app"


def test_verify_auth0_token() -> None:
    token = jwt.encode({"sub": "123", "aud": AUDIENCE, "iss": ISSUER}, SECRET, algorithm="HS256")
    claims = verify_auth0_token(token, SECRET, ISSUER, AUDIENCE)
    assert claims["sub"] == "123"


def test_verify_auth0_token_invalid() -> None:
    # malformed token should raise ValueError
    with pytest.raises(ValueError):
        verify_auth0_token("not-a-token", SECRET, ISSUER, AUDIENCE)


def test_verify_auth0_token_type_check() -> None:
    with pytest.raises(TypeError):
        verify_auth0_token(123, SECRET, ISSUER, AUDIENCE)


@pytest.mark.parametrize(
    "secret,issuer,audience,msg",
    [
        ("", ISSUER, AUDIENCE, "secret required"),
        (SECRET, "", AUDIENCE, "issuer required"),
        (SECRET, ISSUER, "", "audience required"),
    ],
)
def test_verify_auth0_requires_fields(secret, issuer, audience, msg):
    token = jwt.encode({"sub": "123", "aud": AUDIENCE, "iss": ISSUER}, SECRET, algorithm="HS256")
    with pytest.raises(ValueError, match=msg):
        verify_auth0_token(token, secret, issuer, audience)

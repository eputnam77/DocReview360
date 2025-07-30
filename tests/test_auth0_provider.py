from docreview360.auth0_provider import verify_auth0_token
from jose import jwt

SECRET = "secret"
ISSUER = "https://auth.example.com/"
AUDIENCE = "my-app"


def test_verify_auth0_token() -> None:
    token = jwt.encode({"sub": "123", "aud": AUDIENCE, "iss": ISSUER}, SECRET, algorithm="HS256")
    claims = verify_auth0_token(token, SECRET, ISSUER, AUDIENCE)
    assert claims["sub"] == "123"

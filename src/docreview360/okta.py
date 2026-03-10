# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import Any, Dict, cast

from jose import jwt
from jose.exceptions import JWTError


def verify_okta_token(token: str, secret: str, issuer: str, audience: str) -> dict[str, Any]:
    """Validate an Okta JWT and return its claims."""
    if not isinstance(token, str):
        raise TypeError("token must be a string")
    if not token:
        raise ValueError("token required")
    if not secret:
        raise ValueError("secret required")
    if not issuer:
        raise ValueError("issuer required")
    if not audience:
        raise ValueError("audience required")
    try:
        claims = jwt.decode(
            token,
            secret,
            issuer=issuer,
            audience=audience,
            algorithms=["HS256"],
        )
        return cast(Dict[str, Any], claims)
    except JWTError as exc:
        raise ValueError("invalid token") from exc

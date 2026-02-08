from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

import docreview360.api as api_module
from docreview360 import auth
from docreview360.api import app


def _configure_user_repository() -> None:
    base = Path(".tmp") / f"rate-limit-tests-{uuid4().hex}"
    base.mkdir(parents=True, exist_ok=True)
    auth.configure_user_repository(base / "users.db")


def _create_user(username: str, password: str) -> None:
    repo = auth._get_user_repository()
    if repo.get_user(username) is None:
        repo.create_user(username, password)


def test_token_endpoint_rate_limited(monkeypatch) -> None:
    _configure_user_repository()
    password = "StrongPassw0rd!"
    _create_user("ratelimit-token", password)
    monkeypatch.setattr(
        api_module,
        "_TOKEN_RATE_LIMITER",
        api_module._FixedWindowRateLimiter(limit=1, window_seconds=60),
    )
    client = TestClient(app)

    first = client.post("/token", data={"username": "ratelimit-token", "password": password})
    second = client.post("/token", data={"username": "ratelimit-token", "password": password})

    assert first.status_code == 200
    assert second.status_code == 429


def test_login_endpoint_rate_limited(monkeypatch) -> None:
    _configure_user_repository()
    monkeypatch.setattr(
        api_module,
        "_LOGIN_RATE_LIMITER",
        api_module._FixedWindowRateLimiter(limit=1, window_seconds=60),
    )
    client = TestClient(app)

    first = client.post("/login", data={"username": "nobody", "password": "wrong"})
    second = client.post("/login", data={"username": "nobody", "password": "wrong"})

    assert first.status_code == 400
    assert second.status_code == 429


def test_document_import_endpoint_rate_limited(monkeypatch) -> None:
    _configure_user_repository()
    password = "StrongPassw0rd!"
    username = "ratelimit-upload"
    _create_user(username, password)
    token = auth.create_access_token({"sub": username})
    headers = {"Authorization": f"Bearer {token}"}
    monkeypatch.setattr(
        api_module,
        "_UPLOAD_RATE_LIMITER",
        api_module._FixedWindowRateLimiter(limit=1, window_seconds=60),
    )
    client = TestClient(app)

    first = client.post(
        "/documents/import",
        files={"file": ("a.md", b"# First", "text/markdown")},
        headers=headers,
    )
    second = client.post(
        "/documents/import",
        files={"file": ("b.md", b"# Second", "text/markdown")},
        headers=headers,
    )

    assert first.status_code == 201
    assert second.status_code == 429

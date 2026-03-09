from datetime import timedelta
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from docreview360 import auth
from docreview360.api import app
from docreview360.environment import add_environment


def _alice_headers() -> dict[str, str]:
    try:
        auth.USER_REPOSITORY.create_user(
            "alice",
            auth.DEMO_USER_DEFAULTS["alice"]["password"],
            otp_secret=auth.DEMO_USER_DEFAULTS["alice"].get("otp_secret"),
        )
    except Exception:
        pass
    token = auth.create_access_token({"sub": "alice"}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


def test_environment_list_and_switch(tmp_path: Path, monkeypatch: Any) -> None:
    path = tmp_path / "env.yaml"
    add_environment("dev", "http://dev", "green", path)
    add_environment("prod", "http://prod", "red", path)
    monkeypatch.setattr("docreview360.environment.ENV_FILE", path)
    client = TestClient(app)
    hdrs = _alice_headers()

    res = client.get("/environments", headers=hdrs)
    assert res.status_code == 200
    data = res.json()
    assert "dev" in data["envs"] and "prod" in data["envs"]

    res = client.post("/environments/prod", headers=hdrs)
    assert res.status_code == 200
    assert res.json()["url"] == "http://prod"
    assert client.get("/environments", headers=hdrs).json()["current"]["url"] == "http://prod"

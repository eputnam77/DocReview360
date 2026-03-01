from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from docreview360 import auth
from docreview360 import api as api_mod
from docreview360 import config as conf_mod
from docreview360.config import Config


def test_users_me_endpoint(monkeypatch) -> None:
    cfg_dir = Path(".tmp") / f"users-me-{uuid4().hex}"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = cfg_dir / "conf.yaml"
    monkeypatch.setattr(conf_mod, "CONFIG_FILE", cfg_path)
    monkeypatch.setattr(api_mod, "CONFIG_FILE", cfg_path)
    Config(database="sqlite", editor="tiptap", cms="none", auth="oidc").save(cfg_path)

    client = TestClient(api_mod.app)
    token = auth.create_access_token({"sub": "alice"})
    client.cookies.set("access_token", token)
    csrf_token = "csrf-test-token"
    client.cookies.set("csrf_token", csrf_token)
    resp = client.get("/users/me", headers={"X-CSRF-Token": csrf_token})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["username"] == "alice"
    assert payload["inactivity_timeout_minutes"] == 30
    assert payload["branding_company_name"] == "DocReview360"
    assert payload["release_build_number"]
    assert payload["release_build_date"]

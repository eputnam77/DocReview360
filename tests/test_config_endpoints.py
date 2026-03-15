import sys
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from docreview360 import api as api_mod
from docreview360 import auth
from docreview360 import config as conf_mod
from docreview360.config import Config


def test_get_and_update_config(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg_dir = Path(".tmp") / f"config-endpoints-{uuid4().hex}"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = cfg_dir / "conf.yaml"
    monkeypatch.setattr(conf_mod, "CONFIG_FILE", cfg_path)
    monkeypatch.setattr(api_mod, "CONFIG_FILE", cfg_path)
    _admin_router_mod = sys.modules.get("docreview360.api.admin_router")
    if _admin_router_mod is not None:
        monkeypatch.setattr(_admin_router_mod, "CONFIG_FILE", cfg_path)

    Config(
        database="sqlite",
        database_url="sqlite:///test.db",
        editor="tiptap",
        cms="none",
        auth="oidc",
    ).save(cfg_path)
    client = TestClient(api_mod.app)
    token = auth.create_access_token({"sub": "alice"})
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/config", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["database"] == "sqlite"
    assert data["database_url"].startswith("sqlite:///")
    assert data["inactivity_timeout_minutes"] == 30
    assert data["branding_company_name"] == "DocReview360"

    data["database"] = "postgres"
    data["database_url"] = "postgresql://db/prod"
    data["inactivity_timeout_minutes"] = 45
    data["branding_company_name"] = "Acme Reviews"
    data["branding_logo_url"] = "https://example.com/logo.png"
    data["branding_logo_alt"] = "Acme logo"
    resp = client.put("/config", json=data, headers=headers)
    assert resp.status_code == 200
    updated = Config.load(cfg_path)
    assert updated is not None
    assert updated.database == "postgres"
    assert updated.database_url == "postgresql://db/prod"
    assert updated.inactivity_timeout_minutes == 45
    assert updated.branding_company_name == "Acme Reviews"
    assert updated.branding_logo_url == "https://example.com/logo.png"


def test_update_config_rejects_invalid_branding_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg_dir = Path(".tmp") / f"config-branding-{uuid4().hex}"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = cfg_dir / "conf.yaml"
    monkeypatch.setattr(conf_mod, "CONFIG_FILE", cfg_path)
    monkeypatch.setattr(api_mod, "CONFIG_FILE", cfg_path)
    _admin_router_mod = sys.modules.get("docreview360.api.admin_router")
    if _admin_router_mod is not None:
        monkeypatch.setattr(_admin_router_mod, "CONFIG_FILE", cfg_path)

    Config(database="sqlite", editor="tiptap", cms="none", auth="oidc").save(cfg_path)
    client = TestClient(api_mod.app)
    token = auth.create_access_token({"sub": "alice"})
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "database": "sqlite",
        "database_url": "sqlite:///docreview360.db",
        "editor": "tiptap",
        "cms": "none",
        "auth": "oidc",
        "host": "127.0.0.1",
        "port": 8000,
        "debug": False,
        "ai_auto_assign_writers": False,
        "filename_template": "{id}",
        "inactivity_timeout_minutes": 30,
        "branding_company_name": "Acme",
        "branding_logo_url": "https://example.com/logo.bmp",
        "branding_logo_alt": "Acme logo",
        "branding_support_url": "/docs/",
        "branding_docs_url": "/docs/",
        "branding_security_url": "/security",
        "branding_privacy_url": "/privacy",
    }

    resp = client.put("/config", json=payload, headers=headers)
    assert resp.status_code == 422


def test_config_and_signature_provider_require_admin() -> None:
    client = TestClient(api_mod.app)
    repo = auth._get_user_repository()
    if repo.get_user("bob") is None:
        repo.create_user("bob", "BobPass123!AB")

    user_token = auth.create_access_token({"sub": "bob"})
    headers = {"Authorization": f"Bearer {user_token}"}
    payload = {
        "database": "sqlite",
        "database_url": "sqlite:///docreview360.db",
        "editor": "tiptap",
        "cms": "none",
        "auth": "oidc",
        "host": "127.0.0.1",
        "port": 8000,
        "debug": False,
        "ai_auto_assign_writers": False,
        "filename_template": "{id}",
        "inactivity_timeout_minutes": 30,
    }

    assert client.get("/config").status_code == 401
    assert client.get("/config", headers=headers).status_code == 403
    assert client.put("/config", headers=headers, json=payload).status_code == 403
    assert client.get("/signature-provider", headers=headers).status_code == 403
    assert (
        client.put(
            "/signature-provider",
            headers=headers,
            json={"primary": "documenso", "fallback": None},
        ).status_code
        == 403
    )


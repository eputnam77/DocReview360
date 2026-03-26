from pathlib import Path
from uuid import uuid4

from docreview360 import api as api_mod
from docreview360 import config as conf_mod
from docreview360.config import Config
from fastapi.testclient import TestClient


def test_branding_endpoint_defaults(monkeypatch) -> None:
    cfg_dir = Path(".tmp") / f"branding-defaults-{uuid4().hex}"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = cfg_dir / "conf.yaml"
    monkeypatch.setattr(conf_mod, "CONFIG_FILE", cfg_path)
    monkeypatch.setattr(api_mod, "CONFIG_FILE", cfg_path)

    client = TestClient(api_mod.app)
    resp = client.get("/branding")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["branding_company_name"] == "DocReview360"
    assert payload["release_build_number"]
    assert payload["release_build_date"]


def test_branding_endpoint_uses_config(monkeypatch) -> None:
    cfg_dir = Path(".tmp") / f"branding-config-{uuid4().hex}"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = cfg_dir / "conf.yaml"
    monkeypatch.setattr(conf_mod, "CONFIG_FILE", cfg_path)
    monkeypatch.setattr(api_mod, "CONFIG_FILE", cfg_path)

    Config(
        database="sqlite",
        editor="tiptap",
        cms="none",
        auth="oidc",
        branding_company_name="Acme Aviation",
        branding_logo_url="https://example.com/acme-logo.png",
        branding_logo_alt="Acme logo",
    ).save(cfg_path)

    client = TestClient(api_mod.app)
    resp = client.get("/branding")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["branding_company_name"] == "Acme Aviation"
    assert payload["branding_logo_url"] == "https://example.com/acme-logo.png"
    assert payload["branding_logo_alt"] == "Acme logo"

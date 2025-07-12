from fastapi.testclient import TestClient

from docreview360 import api as api_mod
from docreview360 import config as conf_mod
from docreview360.config import Config


def test_get_and_update_config(tmp_path, monkeypatch) -> None:
    cfg_path = tmp_path / "conf.yaml"
    monkeypatch.setattr(conf_mod, "CONFIG_FILE", cfg_path)
    monkeypatch.setattr(api_mod, "CONFIG_FILE", cfg_path)

    Config(database="sqlite", editor="tiptap", cms="none", auth="oidc").save(cfg_path)
    client = TestClient(api_mod.app)

    resp = client.get("/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["database"] == "sqlite"

    data["database"] = "postgres"
    resp = client.put("/config", json=data)
    assert resp.status_code == 200
    updated = Config.load(cfg_path)
    assert updated is not None
    assert updated.database == "postgres"

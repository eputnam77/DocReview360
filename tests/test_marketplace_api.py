from fastapi.testclient import TestClient

from docreview360.api import app
from docreview360.plugin_marketplace import AVAILABLE_PLUGINS


def test_marketplace_list() -> None:
    client = TestClient(app)
    resp = client.get("/plugin-marketplace")
    assert resp.status_code == 200
    assert set(resp.json()) == set(AVAILABLE_PLUGINS)


def test_marketplace_install(monkeypatch) -> None:
    client = TestClient(app)
    called = {}

    def fake_install(name: str) -> None:
        called["name"] = name

    monkeypatch.setattr("docreview360.plugin_marketplace.install_plugin", fake_install)
    resp = client.post("/plugin-marketplace/install", json={"name": "grammar-plugin"})
    assert resp.status_code == 200
    assert resp.json() == {"installed": "grammar-plugin"}
    assert called["name"] == "grammar-plugin"

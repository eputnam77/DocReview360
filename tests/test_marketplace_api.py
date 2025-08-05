from typing import Any

from fastapi.testclient import TestClient
import pytest
from pytest import MonkeyPatch

from docreview360.api import app
from docreview360.plugin_marketplace import PLUGIN_DATA


def test_marketplace_list() -> None:
    client = TestClient(app)
    resp = client.get("/plugin-marketplace")
    assert resp.status_code == 200

    plugins: list[dict[str, Any]] = resp.json()
    assert isinstance(plugins, list)

    # Check that we get the expected number of plugins
    expected_plugin_ids = set(PLUGIN_DATA.keys())
    actual_plugin_ids = {plugin["id"] for plugin in plugins}
    assert actual_plugin_ids == expected_plugin_ids

    # Verify we have real PyPI packages
    assert "language-tool-python" in actual_plugin_ids
    assert "textstat" in actual_plugin_ids
    assert "pypdf2" in actual_plugin_ids

    # Check that each plugin has the required fields
    for plugin in plugins:
        assert "id" in plugin
        assert "name" in plugin
        assert "description" in plugin
        assert "category" in plugin
        assert "version" in plugin
        assert "author" in plugin
        assert "tags" in plugin
        assert isinstance(plugin["tags"], list)


def test_marketplace_install(monkeypatch: MonkeyPatch) -> None:
    client = TestClient(app)
    called = {}

    def fake_install(name: str) -> None:
        called["name"] = name

    monkeypatch.setattr("docreview360.plugin_marketplace.install_plugin", fake_install)
    resp = client.post("/plugin-marketplace/install", json={"name": "grammar-plugin"})
    assert resp.status_code == 200
    assert resp.json() == {"installed": "grammar-plugin"}
    assert called["name"] == "grammar-plugin"


def test_marketplace_install_invalid_plugin(monkeypatch: MonkeyPatch) -> None:
    client = TestClient(app)
    called = {}

    def fake_install(name: str) -> None:
        called["name"] = name
        raise ValueError(f"Unknown plugin: {name}")

    monkeypatch.setattr("docreview360.plugin_marketplace.install_plugin", fake_install)
    resp = client.post("/plugin-marketplace/install", json={"name": "invalid-plugin"})
    assert resp.status_code == 400
    assert "Unknown plugin" in resp.json()["detail"]


def test_marketplace_plugin_info() -> None:
    """Test that plugin information is correctly structured."""
    from docreview360.plugin_marketplace import list_plugins_with_info

    plugins = list_plugins_with_info()

    # Check that we have the expected plugins
    assert len(plugins) == len(PLUGIN_DATA)

    # Check that each plugin has the correct structure
    for plugin in plugins:
        plugin_id = plugin["id"]
        assert plugin_id in PLUGIN_DATA

        # Check that all expected fields are present
        expected_fields = ["name", "description", "category", "version", "author", "tags"]
        for field in expected_fields:
            assert field in plugin
            assert plugin[field] == PLUGIN_DATA[plugin_id][field]

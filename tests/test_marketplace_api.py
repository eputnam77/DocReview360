from datetime import timedelta
from typing import Any

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from docreview360 import auth
from docreview360.api import app
from docreview360.plugin_marketplace import CORE_PLUGIN_DATA, PLUGIN_DATA

ALL_PLUGIN_DATA = {**CORE_PLUGIN_DATA, **PLUGIN_DATA}


def _alice_headers() -> dict[str, str]:
    """Return Authorization headers for a test 'alice' admin user."""
    try:
        auth.USER_REPOSITORY.create_user(
            "alice",
            auth.DEMO_USER_DEFAULTS["alice"]["password"],
            otp_secret=auth.DEMO_USER_DEFAULTS["alice"].get("otp_secret"),
        )
    except Exception:
        pass  # user may already exist
    token = auth.create_access_token({"sub": "alice"}, timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


def test_marketplace_list() -> None:
    client = TestClient(app)
    resp = client.get("/plugin-marketplace", headers=_alice_headers())
    assert resp.status_code == 200

    plugins: list[dict[str, Any]] = resp.json()
    assert isinstance(plugins, list)

    # Check that we get the expected number of plugins
    expected_plugin_ids = set(ALL_PLUGIN_DATA.keys())
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
    resp = client.post(
        "/plugin-marketplace/install",
        json={"name": "grammar-plugin"},
        headers=_alice_headers(),
    )
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
    resp = client.post(
        "/plugin-marketplace/install",
        json={"name": "invalid-plugin"},
        headers=_alice_headers(),
    )
    assert resp.status_code == 400
    assert "Unknown plugin" in resp.json()["detail"]


def test_marketplace_builtin_status() -> None:
    client = TestClient(app)
    resp = client.get("/plugin-marketplace/builtin-status", headers=_alice_headers())
    assert resp.status_code == 200
    assert resp.json() == {"fedstylevalidator": True, "scdocbuilder": True}


def test_marketplace_toggle_builtin_plugin() -> None:
    client = TestClient(app)
    toggle_resp = client.post(
        "/plugin-marketplace/toggle",
        json={"pluginId": "fedstylevalidator", "enabled": False},
        headers=_alice_headers(),
    )
    assert toggle_resp.status_code == 200
    assert toggle_resp.json() == {"pluginId": "fedstylevalidator", "enabled": False}

    status_resp = client.get("/plugin-marketplace/builtin-status", headers=_alice_headers())
    assert status_resp.status_code == 200
    assert status_resp.json()["fedstylevalidator"] is False


def test_marketplace_toggle_rejects_unknown_builtin() -> None:
    client = TestClient(app)
    resp = client.post(
        "/plugin-marketplace/toggle",
        json={"pluginId": "unknown-plugin", "enabled": False},
        headers=_alice_headers(),
    )
    assert resp.status_code == 400
    assert "Unknown built-in plugin" in resp.json()["detail"]


def test_marketplace_plugin_info() -> None:
    """Test that plugin information is correctly structured."""
    from docreview360.plugin_marketplace import list_plugins_with_info

    plugins = list_plugins_with_info()

    # Check that we have the expected plugins
    assert len(plugins) == len(ALL_PLUGIN_DATA)

    # Check that each plugin has the correct structure
    for plugin in plugins:
        plugin_id = plugin["id"]
        assert plugin_id in ALL_PLUGIN_DATA

        # Check that all expected fields are present
        expected_fields = ["name", "description", "category", "version", "author", "tags"]
        for field in expected_fields:
            assert field in plugin
            assert plugin[field] == ALL_PLUGIN_DATA[plugin_id][field]

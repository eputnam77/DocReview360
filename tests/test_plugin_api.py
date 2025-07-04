import sys
from types import ModuleType

from docuflow.api import app
from fastapi.testclient import TestClient


def create_dummy_plugin(name: str) -> str:
    mod = ModuleType(f"{name}_plugin")

    def register(reg):
        reg.register(name, lambda: name)

    mod.register = register
    sys.modules[mod.__name__] = mod
    return mod.__name__


def test_plugin_management_cycle():
    client = TestClient(app)

    module_name = create_dummy_plugin("dummy")

    resp = client.post("/plugins", json={"module": module_name})
    assert resp.status_code == 201
    assert "dummy" in resp.json()["names"]

    resp = client.get("/plugins")
    data = {entry["name"]: entry["enabled"] for entry in resp.json()}
    assert data["dummy"] is True

    resp = client.put("/plugins/dummy/disable")
    assert resp.json() == {"disabled": "dummy"}

    resp = client.get("/plugins")
    data = {entry["name"]: entry["enabled"] for entry in resp.json()}
    assert data["dummy"] is False

    resp = client.put("/plugins/dummy/enable")
    assert resp.json() == {"enabled": "dummy"}

    resp = client.delete("/plugins/dummy")
    assert resp.status_code == 204

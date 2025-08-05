import sys
from types import ModuleType
from typing import Callable, cast

from fastapi.testclient import TestClient

from docreview360.api import app


def create_dummy_plugin(name: str) -> str:
    mod = ModuleType(f"{name}_plugin")

    def register(reg: object) -> None:
        register_fn = cast("Callable[[str, Callable[[], str]], None]", getattr(reg, "register"))
        register_fn(name, lambda: name)

    mod.register = register  # type: ignore[attr-defined]
    sys.modules[mod.__name__] = mod
    return mod.__name__


def test_plugin_management_cycle() -> None:
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

import sys
from datetime import timedelta
from types import ModuleType
from typing import Callable, cast

from fastapi.testclient import TestClient

from docreview360 import auth
from docreview360.api import app


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


def create_dummy_plugin(name: str) -> str:
    mod = ModuleType(f"{name}_plugin")

    def register(reg: object) -> None:
        register_fn = cast("Callable[[str, Callable[[], str]], None]", getattr(reg, "register"))
        register_fn(name, lambda: name)

    mod.register = register
    sys.modules[mod.__name__] = mod
    return mod.__name__


def test_plugin_management_cycle() -> None:
    client = TestClient(app)
    headers = _alice_headers()

    module_name = create_dummy_plugin("dummy")

    resp = client.post("/plugins", json={"module": module_name}, headers=headers)
    assert resp.status_code == 201
    assert "dummy" in resp.json()["names"]

    resp = client.get("/plugins", headers=headers)
    data = {entry["name"]: entry["enabled"] for entry in resp.json()}
    assert data["dummy"] is True

    resp = client.put("/plugins/dummy/disable", headers=headers)
    assert resp.json() == {"disabled": "dummy"}

    resp = client.get("/plugins", headers=headers)
    data = {entry["name"]: entry["enabled"] for entry in resp.json()}
    assert data["dummy"] is False

    resp = client.put("/plugins/dummy/enable", headers=headers)
    assert resp.json() == {"enabled": "dummy"}

    resp = client.delete("/plugins/dummy", headers=headers)
    assert resp.status_code == 204


def test_plugins_requires_auth() -> None:
    """Unauthenticated requests to /plugins and /plugin-marketplace return 401."""
    client = TestClient(app)
    assert client.get("/plugins").status_code == 401
    assert client.get("/plugin-marketplace").status_code == 401

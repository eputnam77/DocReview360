"""Plugin model tests."""

from __future__ import annotations

import sys
from types import ModuleType

from fastapi import FastAPI
from fastapi.testclient import TestClient

from docreview360.plugins import load_plugins, registry
from docreview360.plugins_ui import render_plugin_table

# PL-01


def test_entry_point_registration_appears_in_ui() -> None:
    mod = ModuleType("myplugin")

    def register(reg: object) -> None:
        registry.register("myplugin", lambda: "ok")

    mod.register = register  # type: ignore[attr-defined]
    sys.modules[mod.__name__] = mod
    load_plugins([mod.__name__])
    html = render_plugin_table()
    assert "myplugin" in html


# PL-02

app = FastAPI()
registry.register("tiptap", lambda: "tiptap")
registry.register("onlyoffice", lambda: "onlyoffice")
registry.disable("tiptap")


@app.get("/editor")
def get_editor() -> dict[str, str]:
    plugin = registry.get("onlyoffice")
    return {"editor": plugin()}


def test_hotswap_loads_onlyoffice_when_tiptap_disabled() -> None:
    client = TestClient(app)
    resp = client.get("/editor")
    assert resp.status_code == 200
    assert resp.json()["editor"] == "onlyoffice"

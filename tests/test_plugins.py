import sys
from types import ModuleType
from typing import Any

import pytest

from docreview360.plugins import load_plugins, registry


def test_load_plugins_success() -> None:
    mod = ModuleType("dummy_plugin")

    def register(reg: Any) -> None:
        reg.register("dummy", lambda: "ok")

    setattr(mod, "register", register)
    sys.modules[mod.__name__] = mod

    load_plugins([mod.__name__])
    assert "dummy" in registry.all()


def test_load_plugins_no_register() -> None:
    mod = ModuleType("bad_plugin")
    sys.modules[mod.__name__] = mod
    with pytest.raises(ValueError):
        load_plugins([mod.__name__])


def test_load_plugins_import_error() -> None:
    with pytest.raises(ImportError):
        load_plugins(["nonexistent.plugin"])


def test_registry_enable_disable_cycle() -> None:
    registry.register("p1", lambda: 1)

    registry.disable("p1")
    with pytest.raises(ValueError):
        registry.get("p1")

    registry.enable("p1")
    assert registry.get("p1")() == 1

    registry.unregister("p1")
    with pytest.raises(KeyError):
        registry.get("p1")


def test_registry_duplicate() -> None:
    registry.register("dup", lambda: None)
    with pytest.raises(ValueError):
        registry.register("dup", lambda: None)
    registry.unregister("dup")


def test_registry_info() -> None:
    registry.register("info", lambda: None, enabled=False)
    info = registry.info()
    assert any(p["name"] == "info" and not p["enabled"] for p in info)
    registry.enable("info")
    registry.unregister("info")

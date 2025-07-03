import sys
from types import ModuleType

import pytest

from docuflow.plugins import load_plugins, registry


def test_load_plugins_success():
    mod = ModuleType("dummy_plugin")

    def register(reg):
        reg.register("dummy", lambda: "ok")

    mod.register = register
    sys.modules[mod.__name__] = mod

    load_plugins([mod.__name__])
    assert "dummy" in registry.all()


def test_load_plugins_no_register():
    mod = ModuleType("bad_plugin")
    sys.modules[mod.__name__] = mod
    with pytest.raises(ValueError):
        load_plugins([mod.__name__])


def test_load_plugins_import_error():
    with pytest.raises(ImportError):
        load_plugins(["nonexistent.plugin"])

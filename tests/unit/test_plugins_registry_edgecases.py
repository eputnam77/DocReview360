import pytest
from docreview360.plugins import PluginRegistry


def test_register_rejects_blank_name() -> None:
    registry = PluginRegistry()
    with pytest.raises(ValueError):
        registry.register("   ", lambda: None)


def test_missing_plugins_error_handling() -> None:
    registry = PluginRegistry()
    with pytest.raises(KeyError):
        registry.enable("missing")
    with pytest.raises(KeyError):
        registry.disable("missing")
    with pytest.raises(KeyError):
        registry.unregister("missing")

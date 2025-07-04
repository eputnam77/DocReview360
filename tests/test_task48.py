from docuflow.grammar_plugin import register
from docuflow.plugins import PluginRegistry


def test_grammar_plugin() -> None:
    registry = PluginRegistry()
    register(registry)
    func = registry.get("grammar-checker")
    issues = func("bad bad text")
    assert issues

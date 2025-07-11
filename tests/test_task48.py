from docreview360.grammar_plugin import register
from docreview360.plugins import PluginRegistry


def test_grammar_plugin() -> None:
    registry = PluginRegistry()
    register(registry)
    func = registry.get("grammar-checker")
    issues = func("bad bad text")
    assert issues

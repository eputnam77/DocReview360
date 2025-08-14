from docreview360.plugins import registry
from docreview360.plugins_ui import render_plugin_table


def dummy() -> None:
    pass


def test_render_plugin_table() -> None:
    registry.register("sample", dummy)
    html = render_plugin_table()
    assert "sample" in html
    assert "enabled" in html

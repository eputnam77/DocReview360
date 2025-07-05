from docuflow.contextual_help import get_help, register_help, tooltip_html


def test_help_registry() -> None:
    register_help("editor", "Use the toolbar to format text", "https://loom.com/vid")
    item = get_help("editor")
    assert item is not None and item.text.startswith("Use")
    assert "iframe" in tooltip_html("editor")
    assert get_help("unknown") is None

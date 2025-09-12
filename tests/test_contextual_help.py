import pytest

from docreview360.contextual_help import get_help, register_help, tooltip_html


def test_tooltip_html_escapes_content() -> None:
    """User supplied text and video URLs are safely escaped."""
    register_help("danger", '<b onclick="boom">', 'https://ex.com/?q="on"')
    html = tooltip_html("danger")
    # Dangerous characters should be escaped inside the attributes
    assert '<b onclick="boom">' not in html
    assert '&lt;b onclick=&quot;boom&quot;&gt;' in html
    assert '"on"' not in html  # quote must be escaped in URL attribute


def test_help_registry() -> None:
    register_help("editor", "Use the toolbar to format text", "https://loom.com/vid")
    item = get_help("editor")
    assert item is not None and item.text.startswith("Use")
    assert "iframe" in tooltip_html("editor")
    assert get_help("unknown") is None


def test_invalid_help_inputs_and_missing_tooltip() -> None:
    with pytest.raises(ValueError):
        register_help("", "")
    assert tooltip_html("nope") == ""


def test_topic_lookup_strips_whitespace() -> None:
    register_help(" spaced ", "text")
    assert get_help("spaced") is not None
    assert get_help(" spaced ") is not None
    html = tooltip_html(" spaced ")
    assert html != ""

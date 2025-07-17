from docreview360.stubs.task163 import render_extension_menu


def test_task163_extension_menu_render() -> None:
    """The extension menu renders checkboxes for each extension."""
    html = render_extension_menu(["Bold", "Italic"])
    assert "<div id='extension-menu'" in html
    assert html.count("<input") == 4
    assert "name='Bold'" in html and "checked" in html
    assert "name='Italic'" in html and "checked" in html

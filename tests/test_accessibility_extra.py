from docreview360.accessibility import audit_html


def test_img_alt_single_quotes() -> None:
    html = "<img src='x.png' alt='desc'>"
    assert audit_html(html) == []


def test_button_empty_aria_label() -> None:
    html = "<button aria-label=''> </button>"
    issues = audit_html(html)
    assert "button missing label" in issues


def test_button_nested_empty_span() -> None:
    """Buttons containing only empty tags should still be flagged."""
    html = "<button><span></span></button>"
    issues = audit_html(html)
    assert "button missing label" in issues

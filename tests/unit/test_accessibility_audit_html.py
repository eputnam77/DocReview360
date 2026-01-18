from docreview360.accessibility import audit_html


def test_audit_html_flags_blank_attributes() -> None:
    html = "<img alt='  '><button aria-label='   '></button>"
    issues = audit_html(html)
    assert "image missing alt text" in issues
    assert "button missing label" in issues


def test_audit_html_accepts_valid_labels() -> None:
    html = "<img alt='logo'><button aria-label='Submit'></button>"
    assert audit_html(html) == []

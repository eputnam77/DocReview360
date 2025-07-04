from docuflow.accessibility import audit_html


def test_audit_html_detects_issues() -> None:
    html = "<img src='x.png'><button></button>"
    issues = audit_html(html)
    assert "image missing alt text" in issues
    assert "button missing label" in issues

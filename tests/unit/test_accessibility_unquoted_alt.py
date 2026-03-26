from pathlib import Path

from docreview360 import accessibility

from services.document_checker import run_checks


def test_audit_html_accepts_unquoted_alt() -> None:
    html = '<img src="foo" alt=logo>'
    assert accessibility.audit_html(html) == []


def test_run_checks_accepts_unquoted_alt(tmp_path: Path) -> None:
    html = '<img src="foo" alt=logo>'
    file = tmp_path / "sample.html"
    file.write_text(html)
    result = run_checks(file)
    assert result["accessibility"] == []


def test_img_without_attributes_reports_missing_alt() -> None:
    html = "<img>"
    assert accessibility.audit_html(html) == ["image missing alt text"]


def test_button_accepts_unquoted_aria_label(tmp_path: Path) -> None:
    html = "<button aria-label=Submit></button>"
    assert accessibility.audit_html(html) == []
    file = tmp_path / "btn.html"
    file.write_text(html)
    result = run_checks(file)
    assert result["accessibility"] == []


def test_img_with_unquoted_alt_and_quote_is_flagged(tmp_path: Path) -> None:
    """An unquoted ``alt`` attribute containing a stray quote is invalid HTML
    and should be treated as missing descriptive text."""
    html = '<img src="foo" alt=bar">'
    assert accessibility.audit_html(html) == ["image missing alt text"]
    file = tmp_path / "bad.html"
    file.write_text(html)
    result = run_checks(file)
    assert result["accessibility"] == ["image missing alt text"]

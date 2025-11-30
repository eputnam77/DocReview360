from pathlib import Path

from services.document_checker import run_checks


def test_button_with_empty_aria_label_flagged(tmp_path: Path) -> None:
    file = tmp_path / "doc.html"
    file.write_text("<button aria-label=''></button>")
    result = run_checks(file)
    assert "button missing label" in result["accessibility"]

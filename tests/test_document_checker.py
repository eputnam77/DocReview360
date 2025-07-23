from pathlib import Path

from docreview360.document_checker import run_checks


def test_document_checker_runs(tmp_path: Path) -> None:
    f = tmp_path / "doc.txt"
    f.write_text("hello hello")
    result = run_checks(f)
    assert "grammar" in result

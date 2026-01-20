from pathlib import Path

from docreview360.document_checker import _detect_anomalies, run_checks


def test_run_checks_detects_punctuation_repeats(tmp_path: Path) -> None:
    path = tmp_path / "doc.txt"
    path.write_text("Hello, hello there")
    result = run_checks(path)
    assert "repeated word 'Hello'" in result["grammar"]


def test_run_checks_supports_single_quote_alt(tmp_path: Path) -> None:
    path = tmp_path / "img.html"
    path.write_text("<img src='a.png' alt='desc'>")
    result = run_checks(path)
    assert result["accessibility"] == []


def test_run_checks_empty_nested_button(tmp_path: Path) -> None:
    path = tmp_path / "btn.html"
    path.write_text("<button><span></span></button>")
    result = run_checks(path)
    assert "button missing label" in result["accessibility"]


def test_detect_anomalies_counts_punctuated_repeats() -> None:
    assert _detect_anomalies("bad, bad", threshold=0.5)


def test_detect_anomalies_token_unique_ratio() -> None:
    assert not _detect_anomalies("aaaaaa", threshold=0.48)

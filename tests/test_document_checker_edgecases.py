import gzip
import json
from pathlib import Path

import pytest

from services.document_checker import run_checks
from src.docreview360.backup_utils import restore_backup
from services.document_checker import detect_anomalies


def test_run_checks_detects_punctuation_repeats(tmp_path: Path) -> None:
    path = tmp_path / "doc.txt"
    path.write_text("Hello, hello there")
    result = run_checks(path)
    assert "repeated word 'Hello'" in result["grammar"]


def test_run_checks_supports_single_quote_alt(tmp_path: Path) -> None:
    path = tmp_path / "doc.html"
    path.write_text("<img src='a.png' alt='desc'>")
    result = run_checks(path)
    assert result["accessibility"] == []


def test_run_checks_supports_single_quote_aria_label(tmp_path: Path) -> None:
    """Buttons with single quoted aria labels should pass accessibility checks."""
    path = tmp_path / "btn.html"
    path.write_text("<button aria-label='Go'></button>")
    result = run_checks(path)
    assert result["accessibility"] == []


def test_run_checks_supports_spaced_alt(tmp_path: Path) -> None:
    path = tmp_path / "img-spaced.html"
    path.write_text('<img src="a.png" alt = "desc">')
    result = run_checks(path)
    assert result["accessibility"] == []


def test_run_checks_supports_spaced_aria_label(tmp_path: Path) -> None:
    path = tmp_path / "btn-spaced.html"
    path.write_text('<button aria-label = "Go"></button>')
    result = run_checks(path)
    assert result["accessibility"] == []


def test_run_checks_detects_missing_alt(tmp_path: Path) -> None:
    path = tmp_path / "img-missing.html"
    path.write_text('<img src="a.png">')
    result = run_checks(path)
    assert "image missing alt text" in result["accessibility"]


def test_run_checks_empty_nested_button(tmp_path: Path) -> None:
    path = tmp_path / "btn2.html"
    path.write_text("<button><span></span></button>")
    result = run_checks(path)
    assert "button missing label" in result["accessibility"]


# backup_utils restore invalid base64
def test_restore_backup_invalid_base64(tmp_path: Path) -> None:
    data = {
        "documents": [
            {"id": "1", "content": "x", "yjs_updates": ["!!!"]}
        ],
        "logs": [],
    }
    target = tmp_path / "backup.json.gz"
    with gzip.open(target, "wt", encoding="utf-8") as fh:
        json.dump(data, fh)
    with pytest.raises(ValueError):
        restore_backup(target)


def test_detect_anomalies_counts_punctuated_repeats() -> None:
    """Repeated words separated by punctuation should trigger anomalies."""
    assert detect_anomalies("bad, bad", threshold=0.5)


def test_detect_anomalies_token_unique_ratio() -> None:
    """Uniqueness should be measured on word tokens, not raw characters."""
    # ``"aaaaaa"`` yields a higher anomaly score when uniqueness is measured by
    # characters. Using a threshold between the old and new scores ensures the
    # function now evaluates based on word-level uniqueness.
    assert not detect_anomalies("aaaaaa", threshold=0.48)


import gzip
import json
from pathlib import Path

import pytest

from services.document_checker import run_checks
from src.docreview360.backup_utils import restore_backup


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


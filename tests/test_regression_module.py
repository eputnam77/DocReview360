from __future__ import annotations

import pytest
from docreview360.regression import run_regression


def test_run_regression_counts_nested(tmp_path) -> None:
    (tmp_path / "top.md").write_text("a")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "nested.md").write_text("b")
    assert run_regression(tmp_path) == 2


def test_run_regression_missing_dir(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        run_regression(tmp_path / "missing")

# SPDX-License-Identifier: MIT
from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from docreview360.cli import cli
from docreview360.frontend_assets import extract_frontend_source, frontend_source_root


def test_frontend_source_root_points_to_frontend_tree() -> None:
    root = frontend_source_root()
    assert (root / "package.json").exists()
    assert (root / "pages").exists()


def test_extract_frontend_source_copies_expected_files(tmp_path: Path) -> None:
    target = tmp_path / "frontend-copy"
    extract_frontend_source(target)

    assert (target / "package.json").exists()
    assert (target / "pages" / "index.tsx").exists()
    assert not (target / "node_modules").exists()
    assert not (target / ".next").exists()


def test_extract_frontend_source_rejects_non_empty_destination(tmp_path: Path) -> None:
    target = tmp_path / "frontend-copy"
    target.mkdir()
    (target / "existing.txt").write_text("x", encoding="utf-8")

    with pytest.raises(FileExistsError):
        extract_frontend_source(target)


def test_frontend_cli_path_and_extract(tmp_path: Path) -> None:
    runner = CliRunner()

    path_result = runner.invoke(cli, ["frontend", "path"])
    assert path_result.exit_code == 0
    assert "frontend" in path_result.output.lower()

    target = tmp_path / "cli-frontend"
    extract_result = runner.invoke(cli, ["frontend", "extract", str(target)])
    assert extract_result.exit_code == 0
    assert (target / "package.json").exists()

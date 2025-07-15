from pathlib import Path

from docreview360.stubs.task146 import task146


def test_task146_completed(tmp_path: Path) -> None:
    backup = tmp_path / "bk.json.gz"
    result = task146(str(backup))
    assert Path(result).exists()

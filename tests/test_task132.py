from pathlib import Path

from docreview360.stubs.task132 import task132


def test_task132_completed(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("hello")
    assert task132(tmp_path) == 1

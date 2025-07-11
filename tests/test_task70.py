from pathlib import Path

from docreview360.stubs.task70 import task70


def test_task70(tmp_path: Path) -> None:
    src = tmp_path / "archives"
    src.mkdir()
    (src / "doc.txt").write_text("hi")
    dest = tmp_path / "sp"
    copied = task70(str(src), str(dest))
    assert copied == 1
    assert (dest / "doc.txt").exists()

from pathlib import Path

from docreview360.records import sync_to_sharepoint


def test_sync_to_sharepoint(tmp_path: Path) -> None:
    src = tmp_path / "archives"
    dest = tmp_path / "sp"
    src.mkdir()
    file1 = src / "a.txt"
    file1.write_text("x")
    copied = sync_to_sharepoint(src, dest)
    assert copied == 1
    assert (dest / "a.txt").exists()

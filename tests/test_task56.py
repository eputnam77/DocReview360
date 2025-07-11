from pathlib import Path

from docreview360.stubs.task56 import task56


def test_task56_upload(tmp_path: Path) -> None:
    bucket = tmp_path / "bucket"
    path = task56(bucket, "file.txt", b"data")
    assert path.read_bytes() == b"data"

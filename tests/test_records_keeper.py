from pathlib import Path

from docreview360.records_keeper import create_archival_folder


def test_create_archival_folder(tmp_path: Path) -> None:
    folder = create_archival_folder(tmp_path, "proj")
    assert folder.exists()
    assert folder.parent.name == "proj"

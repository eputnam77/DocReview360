from __future__ import annotations

from pathlib import Path

from docreview360.records import sync_to_sharepoint
from pytest import MonkeyPatch


def test_sync_to_sharepoint_expands_home(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "example.txt").write_text("data")

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("SHAREPOINT_ROOT", "~/records")

    copied = sync_to_sharepoint(src)

    dest = tmp_path / "records"
    assert copied == 1
    assert (dest / "example.txt").read_text() == "data"

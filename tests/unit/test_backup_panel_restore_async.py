from pathlib import Path

import docreview360.backup_panel as panel
import pytest


def test_restore_backup_async_invokes_dependencies(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    called: dict[str, object] = {}

    def fake_restore(path: Path) -> None:
        called["path"] = path

    def fake_record(task_id: int) -> None:
        called["task_id"] = task_id

    monkeypatch.setattr(panel, "restore_backup", fake_restore)

    panel.restore_backup_async(str(tmp_path))

    assert called["path"] == tmp_path

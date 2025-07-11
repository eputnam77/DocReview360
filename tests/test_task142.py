import pytest

from docreview360.settings_manager import load_settings
from docreview360.stubs.task142 import task142


def test_task142_completed(tmp_path) -> None:
    path = tmp_path / "settings.yaml"
    task142(path=path)
    assert load_settings(path)["smtp_host"] == "localhost"


def test_load_settings_invalid(tmp_path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("\t:\n- bad")
    with pytest.raises(ValueError):
        load_settings(path)

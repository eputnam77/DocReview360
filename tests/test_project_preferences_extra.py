from __future__ import annotations

import pathlib

from docreview360 import project_preferences as pp


def test_update_preferences_coerces_string_bools(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "prefs.yaml"
    prefs = pp.update_project_preferences(
        "proj", {"lint": "false", "collab": "TRUE", "unknown": "1"}, path=path
    )
    assert prefs.lint is False
    assert prefs.collab is True
    # unknown key should be ignored
    data = pp.get_project_preferences("proj", path=path)
    assert hasattr(data, "lint") and data.lint is False
    assert "unknown" not in data.model_dump()

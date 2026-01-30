from pathlib import Path

import pytest

from docreview360.environment import add_environment, load_envs


def test_add_environment_validates_inputs(tmp_path: Path) -> None:
    path = tmp_path / "env.yaml"
    with pytest.raises(ValueError):
        add_environment(" ", "url", "color", path)
    with pytest.raises(ValueError):
        add_environment("name", " ", "color", path)
    with pytest.raises(ValueError):
        add_environment("name", "url", " ", path)


def test_load_envs_rejects_invalid_entries(tmp_path: Path) -> None:
    path = tmp_path / "env.yaml"
    path.write_text(
        """
        prod:
          url: 123
          color: blue
        """,
    )
    with pytest.raises(ValueError, match="Environment url must be a non-empty string"):
        load_envs(path)

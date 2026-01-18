from pathlib import Path

import pytest

from docreview360.environment import add_environment


def test_add_environment_validates_inputs(tmp_path: Path) -> None:
    path = tmp_path / "env.yaml"
    with pytest.raises(ValueError):
        add_environment(" ", "url", "color", path)
    with pytest.raises(ValueError):
        add_environment("name", " ", "color", path)
    with pytest.raises(ValueError):
        add_environment("name", "url", " ", path)

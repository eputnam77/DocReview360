from pathlib import Path
import pytest

from docreview360.environment import load_envs


def test_load_envs_invalid_yaml(tmp_path: Path) -> None:
    config = tmp_path / "env.yaml"
    config.write_text(":\n- bad")
    with pytest.raises(ValueError):
        load_envs(config)

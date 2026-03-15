import os
from pathlib import Path

import pytest

from docreview360 import environment


def test_add_environment_creates_dir(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "envs.yaml"
    environment.add_environment("dev", "http://dev", "green", path)
    assert path.exists()
    assert environment.load_envs(path)["dev"]["url"] == "http://dev"


def test_load_envs_non_mapping(tmp_path: Path) -> None:
    file = tmp_path / "env.yaml"
    file.write_text("- just\n- a\n- list\n")
    with pytest.raises(ValueError):
        environment.load_envs(file)


def test_switch_environment_strips_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = tmp_path / "envs.yaml"
    environment.add_environment("staging", "https://staging", "blue", env_file)

    # Register the env var with monkeypatch so it is cleaned up after the test.
    monkeypatch.delenv("DOCREVIEW360_ENV", raising=False)
    url = environment.switch_environment("  staging  ", env_file)

    assert url == "https://staging"
    assert os.getenv("DOCREVIEW360_ENV") == "staging"

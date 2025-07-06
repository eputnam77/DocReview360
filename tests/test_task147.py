import os

import pytest

from docuflow.environment import load_envs
from docuflow.stubs.task147 import task147


def test_task147_completed(tmp_path) -> None:
    env_file = tmp_path / "env.yaml"
    url = task147(path=env_file)
    assert load_envs(env_file)["stage"]["url"] == url
    assert os.environ.get("DOCUFLOW_ENV") == "stage"


def test_load_envs_missing(tmp_path) -> None:
    from docuflow.environment import load_envs

    path = tmp_path / "missing.yaml"
    assert load_envs(path) == {}


def test_switch_unknown_env(tmp_path) -> None:
    from docuflow.environment import switch_environment

    with pytest.raises(KeyError):
        switch_environment("nope", path=tmp_path / "env.yaml")

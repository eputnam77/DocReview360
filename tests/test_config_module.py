from pathlib import Path

import pytest
from docreview360.config import Config


def test_config_roundtrip(tmp_path: Path) -> None:
    cfg = Config(
        database="sqlite",
        database_url="sqlite:///test.db",
        editor="tiptap",
        cms="none",
        auth="oidc",
    )
    path = tmp_path / "conf.yaml"
    cfg.save(path)
    loaded = Config.load(path)
    assert loaded == cfg


def test_config_load_bad_yaml(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("::invalid::yaml")
    with pytest.raises(ValueError):
        Config.load(path)

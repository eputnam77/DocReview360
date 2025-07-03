from pathlib import Path

from docuflow.config import Config


def test_config_roundtrip(tmp_path: Path) -> None:
    cfg = Config(database="sqlite", editor="tiptap", cms="none", auth="oidc")
    path = tmp_path / "conf.yaml"
    cfg.save(path)
    loaded = Config.load(path)
    assert loaded == cfg

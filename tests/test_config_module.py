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


def test_config_debug_rejected_in_production_like_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "prod-debug.yaml"
    path.write_text("database: sqlite\neditor: tiptap\ncms: none\nauth: oidc\ndebug: true")
    monkeypatch.setenv("DOCREVIEW360_ENV", "production")

    with pytest.raises(ValueError, match="debug must be disabled"):
        Config.load(path)


def test_config_debug_allowed_in_dev_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "dev-debug.yaml"
    path.write_text("database: sqlite\neditor: tiptap\ncms: none\nauth: oidc\ndebug: true")
    monkeypatch.setenv("DOCREVIEW360_ENV", "dev")

    loaded = Config.load(path)
    assert loaded is not None
    assert loaded.debug is True

def test_config_rejects_prod_alias_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "prod-alias.yaml"
    path.write_text("database: sqlite\neditor: tiptap\ncms: none\nauth: oidc\ndebug: false")
    monkeypatch.setenv("DOCREVIEW360_ENV", "prod")

    with pytest.raises(ValueError, match="DOCREVIEW360_ENV must be set to 'production'"):
        Config.load(path)

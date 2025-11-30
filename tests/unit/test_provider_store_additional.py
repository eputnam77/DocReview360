from pathlib import Path

import pytest
import yaml

import docreview360.provider_store as ps


def test_load_providers_rejects_non_mapping(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = tmp_path / "providers.yaml"
    # Provider defined as a simple string instead of mapping should be rejected
    cfg.write_text("documenso: invalid")
    monkeypatch.setattr(ps, "PROVIDERS_FILE", cfg)
    with pytest.raises(ValueError):
        ps.load_providers()


def test_load_providers_defaults_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the providers file is absent the built-in defaults are returned."""
    cfg = tmp_path / "providers.yaml"
    monkeypatch.setattr(ps, "PROVIDERS_FILE", cfg)
    data = ps.load_providers()
    assert data["documenso"]["priority"] == 1


def test_set_provider_health_persists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Updating health should write the change to disk."""
    cfg = tmp_path / "providers.yaml"
    monkeypatch.setattr(ps, "PROVIDERS_FILE", cfg)
    ps.set_provider_health("documenso", False)
    saved = yaml.safe_load(cfg.read_text())
    assert saved["documenso"]["healthy"] is False


def test_load_providers_root_not_mapping(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Top-level YAML structures other than a mapping should be rejected."""
    cfg = tmp_path / "providers.yaml"
    cfg.write_text("- a\n- b")
    monkeypatch.setattr(ps, "PROVIDERS_FILE", cfg)
    with pytest.raises(ValueError):
        ps.load_providers()

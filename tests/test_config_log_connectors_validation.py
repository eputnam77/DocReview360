from pathlib import Path

import pytest
import yaml
from docreview360.config import Config


def test_log_connector_entries_must_be_dict(tmp_path: Path) -> None:
    data = {
        "database": "sqlite",
        "editor": "tiptap",
        "cms": "none",
        "auth": "oidc",
        "log_connectors": ["not-a-dict"],
    }
    path = tmp_path / "cfg.yaml"
    path.write_text(yaml.safe_dump(data))
    with pytest.raises(ValueError):
        Config.load(path)


def _write_config(path: Path, batch_size: str | int) -> None:
    data = {
        "database": "sqlite",
        "editor": "tiptap",
        "cms": "none",
        "auth": "oidc",
        "log_connectors": [
            {"type": "elk", "endpoint": "http://example.test", "batch_size": batch_size}
        ],
    }
    path.write_text(yaml.safe_dump(data))


def test_log_connector_batch_size_must_be_positive(tmp_path: Path) -> None:
    path = tmp_path / "cfg.yaml"
    _write_config(path, 0)
    with pytest.raises(ValueError, match="batch_size must be a positive integer"):
        Config.load(path)


def test_log_connector_batch_size_must_be_numeric(tmp_path: Path) -> None:
    path = tmp_path / "cfg.yaml"
    _write_config(path, "high")
    with pytest.raises(ValueError, match="batch_size must be a positive integer"):
        Config.load(path)


def test_log_connector_batch_size_coerces_numeric_strings(tmp_path: Path) -> None:
    path = tmp_path / "cfg.yaml"
    _write_config(path, "3")
    config = Config.load(path)
    assert config is not None
    assert config.log_connectors[0].batch_size == 3

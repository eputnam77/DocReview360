import yaml
import pytest
from pathlib import Path
from docreview360.config import Config


def test_log_connector_entries_must_be_dict(tmp_path: Path) -> None:
    data = {
        'database': 'sqlite',
        'editor': 'tiptap',
        'cms': 'none',
        'auth': 'oidc',
        'log_connectors': ['not-a-dict']
    }
    path = tmp_path / 'cfg.yaml'
    path.write_text(yaml.safe_dump(data))
    with pytest.raises(ValueError):
        Config.load(path)

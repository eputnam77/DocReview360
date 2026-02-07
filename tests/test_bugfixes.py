import gzip
from pathlib import Path

import pytest

from docreview360 import backup_utils, email_templates, event_dispatcher


def test_restore_backup_invalid_json(tmp_path: Path):
    bad = tmp_path / "bad.gz"
    with gzip.open(bad, "wt", encoding="utf-8") as fh:
        fh.write("not json")
    with pytest.raises(ValueError):
        backup_utils.restore_backup(bad)


def test_create_template_strips_and_rejects_duplicates(tmp_path: Path):
    email_templates.reset_email_templates(root=tmp_path / "email_templates.json")
    tmpl = email_templates.create_template(" name ", "subject", "body")
    assert tmpl.name == "name"
    assert "name" in email_templates.TEMPLATES
    with pytest.raises(ValueError):
        email_templates.create_template("name", "s", "b")


def test_event_dispatcher_validates_types():
    with pytest.raises(TypeError):
        event_dispatcher.EventDispatcher(retries=1.5)
    with pytest.raises(TypeError):
        event_dispatcher.EventDispatcher(retries=1, backoff="0")

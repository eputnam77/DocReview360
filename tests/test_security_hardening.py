from pathlib import Path

import pytest
from docreview360.celery_app import app
from docreview360.security_hardening import (
    enable_fedramp_backup,
    enforce_mfa_login,
    import_realm_file,
    secure_backup,
)


def test_import_realm_file(tmp_path: Path) -> None:
    p = tmp_path / "realm.json"
    p.write_text('{"realm": "demo"}')
    data = import_realm_file(str(p))
    assert data["realm"] == "demo"


def test_import_realm_file_invalid(tmp_path: Path) -> None:
    p = tmp_path / "realm.json"
    p.write_text("{}")
    with pytest.raises(ValueError):
        import_realm_file(str(p))


def test_enforce_mfa_login() -> None:
    token = enforce_mfa_login("admin", "secret", "123456")
    assert isinstance(token, str)


def test_enable_fedramp_backup(tmp_path: Path) -> None:
    dest = tmp_path / "b.gz"
    enable_fedramp_backup(str(dest))
    schedule = app.conf.beat_schedule["fedramp_backup"]
    assert schedule["task"] == "docreview360.secure_backup"
    # run task to ensure it works
    result = secure_backup(str(dest))
    assert Path(result).exists()

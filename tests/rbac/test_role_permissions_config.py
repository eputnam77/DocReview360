from __future__ import annotations

import os
from pathlib import Path

import yaml

from docreview360 import rbac


def test_role_permissions_override_refreshes_cache(tmp_path: Path, monkeypatch) -> None:
    settings_path = tmp_path / "settings.yaml"
    monkeypatch.setattr(rbac.settings_manager, "SETTINGS_FILE", settings_path)

    settings_path.write_text(
        yaml.safe_dump({"rbac": {"roles": {"admin": ["create"], "user": ["read"]}}})
    )
    rbac.reload_role_permissions(force=True)

    rbac.configure_role_repository(tmp_path / "roles.db")
    rbac.reset_role_assignments(include_defaults=False)
    rbac.set_user_roles("alice", ["admin"])

    assert rbac.get_role_permissions()["admin"] == {"create"}
    assert rbac.has_permission("alice", "create")
    assert not rbac.has_permission("alice", "delete")

    settings_path.write_text(yaml.safe_dump({"rbac": {"roles": {"admin": ["delete"]}}}))
    stat = settings_path.stat()
    os.utime(settings_path, (stat.st_atime + 1, stat.st_mtime + 1))
    rbac.reload_role_permissions(force=True)

    assert rbac.has_permission("alice", "delete")
    assert not rbac.has_permission("alice", "create")

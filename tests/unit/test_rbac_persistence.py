from __future__ import annotations

import importlib
import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _clear_import() -> None:
    if "docreview360.rbac" in sys.modules:
        del sys.modules["docreview360.rbac"]
    yield
    if "docreview360.rbac" in sys.modules:
        del sys.modules["docreview360.rbac"]


def test_roles_survive_module_reload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "roles.db"
    monkeypatch.setenv("DOCREVIEW360_RBAC_DB", str(db_path))
    rbac = importlib.import_module("docreview360.rbac")
    rbac.set_user_roles("eve", ["manager"])
    assert rbac.has_role("eve", "manager")

    reloaded = importlib.reload(rbac)
    assert reloaded.has_permission("eve", "update")


def test_roles_persist_across_processes(tmp_path: Path) -> None:
    db_path = tmp_path / "roles.db"
    env = os.environ.copy()
    env["DOCREVIEW360_RBAC_DB"] = str(db_path)
    project_root = Path(__file__).resolve().parents[2]
    src_path = project_root / "src"
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(src_path) if not existing else str(src_path) + os.pathsep + existing

    writer = f"""
import os
os.environ['DOCREVIEW360_RBAC_DB'] = {str(db_path)!r}
from docreview360 import rbac
rbac.set_user_roles('frank', ['editor'])
"""
    subprocess.run([sys.executable, "-c", writer], check=True, env=env)

    reader = f"""
import os
os.environ['DOCREVIEW360_RBAC_DB'] = {str(db_path)!r}
from docreview360 import rbac
import sys
sys.exit(0 if rbac.has_permission('frank', 'update') else 1)
"""
    result = subprocess.run([sys.executable, "-c", reader], env=env)
    assert result.returncode == 0

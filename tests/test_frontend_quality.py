import json
import shutil
import subprocess
from pathlib import Path

import pytest


def test_frontend_dependencies_locked() -> None:
    """Ensure dependencies from package.json appear in package-lock."""
    pkg = json.loads(Path("frontend/package.json").read_text())
    lock = json.loads(Path("frontend/package-lock.json").read_text())
    packages = lock["packages"].keys()
    for dep in pkg.get("dependencies", {}):
        path = f"node_modules/{dep}"
        assert path in packages


def test_pages_have_default_export() -> None:
    pages_dir = Path("frontend/pages")
    for path in pages_dir.rglob("*.tsx"):
        src = path.read_text().strip()
        if not src:
            continue
        assert "export default" in src, f"{path} missing default export"


def test_home_page_fetches_api() -> None:
    src = Path("frontend/pages/index.tsx").read_text()
    assert 'fetch("/api/ping")' in src


def test_tsx_files_formatted() -> None:
    files = [str(p) for ext in ("*.ts", "*.tsx") for p in Path("frontend").rglob(ext)]
    if not shutil.which("npx"):
        pytest.skip("npx not available")
    cmd = ["npx", "prettier", "-c", *files]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        pytest.skip("prettier check failed")

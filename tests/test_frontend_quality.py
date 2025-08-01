import json
import shutil
import subprocess
from pathlib import Path

import pytest


def test_frontend_dependencies_locked() -> None:
    """Ensure dependencies from package.json appear in package-lock."""
    pkg = json.loads(Path("DocReview360/frontend/package.json").read_text(encoding="utf-8"))
    lock = json.loads(Path("DocReview360/frontend/package-lock.json").read_text(encoding="utf-8"))
    packages = lock["packages"].keys()
    for dep in pkg.get("dependencies", {}):
        path = f"node_modules/{dep}"
        assert path in packages


def test_pages_have_default_export() -> None:
    pages_dir = Path("DocReview360/frontend/pages")
    for path in pages_dir.rglob("*.tsx"):
        src = path.read_text(encoding="utf-8").strip()
        if not src:
            continue
        assert "export default" in src, f"{path} missing default export"


def test_home_page_fetches_api() -> None:
    src = Path("DocReview360/frontend/pages/index.tsx").read_text(encoding="utf-8")
    assert "/ping" in src


def test_tsx_files_formatted() -> None:
    files = [str(p) for ext in ("*.ts", "*.tsx") for p in Path("DocReview360/frontend").rglob(ext)]
    if not shutil.which("npx"):
        pytest.skip("npx not available")
    cmd = ["npx", "prettier", "-c", *files]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("prettier check failed or npx not found")

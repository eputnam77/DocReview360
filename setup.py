from __future__ import annotations

import shutil
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py

_REPO_ROOT = Path(__file__).resolve().parent
_FRONTEND_SOURCE = _REPO_ROOT / "frontend"
_SKIP_DIR_NAMES = {"node_modules", ".next", ".tmp", "__pycache__", "__tests__", "scripts"}
_SKIP_FILE_NAMES = {".env.local"}
_SKIP_RELATIVE_PATHS = {
    Path("data/mock.js"),
    Path("data/mock.ts"),
    Path("public/sample.txt"),
}
_SKIP_SUFFIXES = {".db", ".sqlite", ".log", ".pyc", ".tmp", ".tsbuildinfo"}


def _should_copy_file(path: Path, relative_path: Path) -> bool:
    return (
        path.name not in _SKIP_FILE_NAMES
        and path.suffix not in _SKIP_SUFFIXES
        and relative_path not in _SKIP_RELATIVE_PATHS
    )


def _sync_frontend_bundle(destination: Path) -> None:
    if not _FRONTEND_SOURCE.exists():
        return

    destination.mkdir(parents=True, exist_ok=True)
    for child in destination.iterdir():
        if child.name == "__init__.py":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()

    for source_path in _FRONTEND_SOURCE.rglob("*"):
        relative_path = source_path.relative_to(_FRONTEND_SOURCE)
        if any(part in _SKIP_DIR_NAMES for part in relative_path.parts):
            continue
        if source_path.is_dir():
            (destination / relative_path).mkdir(parents=True, exist_ok=True)
            continue
        if not _should_copy_file(source_path, relative_path):
            continue
        target_path = destination / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)


class build_py(_build_py):
    def run(self) -> None:
        super().run()
        frontend_target = Path(self.build_lib) / "docreview360" / "frontend_src"
        _sync_frontend_bundle(frontend_target)


setup(cmdclass={"build_py": build_py})

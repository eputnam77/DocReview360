from __future__ import annotations

import shutil
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py

_REPO_ROOT = Path(__file__).resolve().parent
_FRONTEND_SOURCE = _REPO_ROOT / "frontend"
_FRONTEND_BUILD_CANDIDATES = (
    _FRONTEND_SOURCE / "out",
    _FRONTEND_SOURCE / ".next" / "standalone",
    _FRONTEND_SOURCE / ".next",
)
_SKIP_DIR_NAMES = {
    "node_modules",
    ".tmp",
    "__pycache__",
    "__tests__",
    "cache",
    "dev",
    "diagnostics",
    "server",
    "types",
}
_SKIP_FILE_NAMES = {".env.local"}
_SKIP_RELATIVE_PATHS = {
    Path("data/mock.js"),
    Path("data/mock.ts"),
    Path("public/sample.txt"),
}
_SKIP_SUFFIXES = {".db", ".sqlite", ".log", ".map", ".pyc", ".tmp", ".tsbuildinfo"}
_OPTIONAL_ARTIFACT_SUFFIXES = {".onnx", ".pt", ".pkl", ".db", ".sqlite"}
_STALE_BUILD_DIRS = (
    Path("frontend_src"),
    Path("ml") / "assets",
)


def _should_copy_file(path: Path, relative_path: Path) -> bool:
    return (
        path.name not in _SKIP_FILE_NAMES
        and path.suffix not in _SKIP_SUFFIXES
        and relative_path not in _SKIP_RELATIVE_PATHS
    )


def _sync_frontend_bundle(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for child in destination.iterdir():
        if child.name == "__init__.py":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()

    source_root = next((path for path in _FRONTEND_BUILD_CANDIDATES if path.exists()), None)
    if source_root is None:
        marker = destination / "README.txt"
        marker.write_text(
            "No built frontend bundle was available when this wheel was built.\n"
            "Run the frontend build before creating release artifacts.\n",
            encoding="utf-8",
        )
        return

    for source_path in source_root.rglob("*"):
        relative_path = source_path.relative_to(source_root)
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


def _remove_stale_build_artifacts(build_lib: str) -> None:
    package_root = Path(build_lib) / "docreview360"
    for relative_dir in _STALE_BUILD_DIRS:
        target = package_root / relative_dir
        if target.exists():
            shutil.rmtree(target)

    if not package_root.exists():
        return
    for candidate in package_root.rglob("*"):
        if candidate.is_file() and candidate.suffix in _OPTIONAL_ARTIFACT_SUFFIXES:
            candidate.unlink()


class build_py(_build_py):
    def run(self) -> None:
        super().run()
        _remove_stale_build_artifacts(self.build_lib)
        frontend_target = Path(self.build_lib) / "docreview360" / "frontend_static"
        _sync_frontend_bundle(frontend_target)


setup(cmdclass={"build_py": build_py})

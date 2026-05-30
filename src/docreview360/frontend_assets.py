# SPDX-License-Identifier: MIT
"""Helpers for accessing the bundled frontend build artifact."""

from __future__ import annotations

import shutil
from pathlib import Path

_SKIP_DIR_NAMES = {
    "node_modules",
    ".tmp",
    "__pycache__",
    "__tests__",
    "scripts",
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


def _should_copy_file(path: Path, relative_path: Path) -> bool:
    return (
        path.name not in _SKIP_FILE_NAMES
        and path.suffix not in _SKIP_SUFFIXES
        and relative_path not in _SKIP_RELATIVE_PATHS
    )


def _packaged_frontend_root() -> Path:
    return Path(__file__).resolve().parent / "frontend_static"


def _repo_frontend_build_roots() -> tuple[Path, ...]:
    root = Path(__file__).resolve().parents[2] / "frontend"
    return (
        root / "out",
        root / ".next" / "standalone",
        root / ".next",
    )


def _has_frontend_payload(path: Path) -> bool:
    ignored = {"__init__.py", "README.txt", "__pycache__"}
    return any(child.name not in ignored for child in path.iterdir())


def frontend_source_root() -> Path:
    """Return the available built frontend bundle for this install."""

    for candidate in (_packaged_frontend_root(), *_repo_frontend_build_roots()):
        if candidate.exists() and _has_frontend_payload(candidate):
            return candidate
    raise FileNotFoundError(
        "DocReview360 built frontend assets are not available in this installation"
    )


def extract_frontend_source(destination: Path, *, force: bool = False) -> Path:
    """Copy the bundled frontend build artifact to ``destination``."""

    source = frontend_source_root()
    if destination.exists():
        if not destination.is_dir():
            raise NotADirectoryError(f"{destination} is not a directory")
        if any(destination.iterdir()) and not force:
            raise FileExistsError(f"{destination} is not empty")
    else:
        destination.mkdir(parents=True, exist_ok=True)

    for source_path in source.rglob("*"):
        relative_path = source_path.relative_to(source)
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

    return destination

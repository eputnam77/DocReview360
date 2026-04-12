# SPDX-License-Identifier: MIT
"""Helpers for accessing the bundled frontend source tree."""

from __future__ import annotations

import shutil
from pathlib import Path

_SKIP_DIR_NAMES = {"node_modules", ".next", ".tmp", "__pycache__"}
_SKIP_FILE_NAMES = {".env.local"}
_SKIP_SUFFIXES = {".db", ".sqlite", ".log", ".pyc", ".tmp", ".tsbuildinfo"}


def _should_copy_file(path: Path) -> bool:
    return path.name not in _SKIP_FILE_NAMES and path.suffix not in _SKIP_SUFFIXES


def _packaged_frontend_root() -> Path:
    return Path(__file__).resolve().parent / "frontend_src"


def _repo_frontend_root() -> Path:
    return Path(__file__).resolve().parents[2] / "frontend"


def frontend_source_root() -> Path:
    """Return the available frontend source tree for this install."""

    for candidate in (_packaged_frontend_root(), _repo_frontend_root()):
        if (candidate / "package.json").exists():
            return candidate
    raise FileNotFoundError("DocReview360 frontend source is not available in this installation")


def extract_frontend_source(destination: Path, *, force: bool = False) -> Path:
    """Copy the bundled frontend source tree to ``destination``."""

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
        if not _should_copy_file(source_path):
            continue
        target_path = destination / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)

    return destination

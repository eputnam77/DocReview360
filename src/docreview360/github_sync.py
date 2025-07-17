"""Lightweight GitHub document sync utilities."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def _run(cmd: list[str], cwd: Path) -> None:
    """Run a git command in ``cwd`` ensuring success."""
    subprocess.run(cmd, cwd=cwd, check=True)


def push_document(doc: Path, repo: Path, branch: str = "main") -> str:
    """Commit ``doc`` to ``repo`` and return the commit hash."""
    repo.mkdir(parents=True, exist_ok=True)
    if not (repo / ".git").exists():
        _run(["git", "init"], repo)
        _run(["git", "checkout", "-b", branch], repo)
    dest = repo / doc.name
    shutil.copy2(doc, dest)
    _run(["git", "add", dest.name], repo)
    _run(["git", "commit", "-m", "Sync document"], repo)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo).decode().strip()
    return commit


def pull_document(name: str, repo: Path) -> bytes:
    """Return the bytes of ``name`` from ``repo`` after an optional pull."""
    if (repo / name).exists():
        return (repo / name).read_bytes()
    raise FileNotFoundError(name)

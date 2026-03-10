# SPDX-License-Identifier: MIT
"""Lightweight GitHub document sync utilities."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def _ensure_repo(repo: Path, branch: str, remote: Path | None) -> None:
    """Initialize ``repo`` as a git repository if needed.

    Optionally sets the ``remote`` URL and creates ``branch`` if the
    repository didn't exist. This avoids re-running ``git init`` for
    subsequent calls and keeps the helper idempotent.
    """
    repo.mkdir(parents=True, exist_ok=True)
    if not (repo / ".git").exists():
        _run(["git", "init"], repo)
        _run(["git", "checkout", "-b", branch], repo)
        if remote:
            _run(["git", "remote", "add", "origin", str(remote)], repo)


def _run(cmd: list[str], cwd: Path) -> None:
    """Run a git command in ``cwd`` ensuring success."""
    subprocess.run(cmd, cwd=cwd, check=True)


def push_document(doc: Path, repo: Path, branch: str = "main", remote: Path | None = None) -> str:
    """Commit ``doc`` to ``repo`` and return the commit hash.

    When ``remote`` is provided the commit is also pushed to that
    repository. This supports local bare repos for offline usage.
    """
    _ensure_repo(repo, branch, remote)
    dest = repo / doc.name
    shutil.copy2(doc, dest)
    _run(["git", "add", dest.name], repo)
    _run(["git", "commit", "-m", "Sync document"], repo)
    if remote:
        _run(["git", "push", "-u", "origin", branch], repo)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo).decode().strip()
    return commit


def pull_document(name: str, repo: Path, remote: Path | None = None, branch: str = "main") -> bytes:
    """Return the bytes of ``name`` from ``repo``.

    If ``remote`` is given and ``repo`` does not exist it will be cloned.
    Subsequent calls perform ``git pull`` to fetch the latest version.
    """
    if remote:
        if not (repo / ".git").exists():
            # ``git clone`` fails when the destination directory's parent does
            # not exist.  Ensure the path is created so callers may request
            # nested repository locations without manual setup.
            repo.parent.mkdir(parents=True, exist_ok=True)
            _run(["git", "clone", "-b", branch, str(remote), str(repo)], repo.parent)
        else:
            _run(["git", "pull", "origin", branch], repo)
    dest = repo / name
    if dest.exists():
        return dest.read_bytes()
    raise FileNotFoundError(name)

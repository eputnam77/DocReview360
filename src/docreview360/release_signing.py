# SPDX-License-Identifier: MIT
"""Release tag signing and verification helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path


def create_signed_git_tag(
    tag: str,
    *,
    message: str,
    key_id: str | None = None,
    repo_root: Path | None = None,
) -> str:
    """Create a signed annotated git tag and return git output."""

    cmd = ["git", "tag", "-s"]
    if key_id:
        cmd.extend(["-u", key_id])
    cmd.extend([tag, "-m", message])

    completed = subprocess.run(
        cmd,
        check=True,
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    return (completed.stdout or "") + (completed.stderr or "")


def verify_git_tag_signature(tag: str, *, repo_root: Path | None = None) -> str:
    """Verify a git tag signature and return verification output."""

    completed = subprocess.run(
        ["git", "verify-tag", tag],
        check=True,
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    return (completed.stdout or "") + (completed.stderr or "")

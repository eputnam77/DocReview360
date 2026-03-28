# SPDX-License-Identifier: MIT
"""Shared file-hashing utility used across ML modules."""

from __future__ import annotations

import hashlib
from pathlib import Path


def file_sha256(path: Path) -> str:
    """Return the hex SHA-256 digest of *path*, reading in 8 KiB chunks."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()

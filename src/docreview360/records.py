# SPDX-License-Identifier: MIT
"""Utilities for syncing archive files to a SharePoint records repository."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional

from .sharepoint import SharePointClient


def sync_to_sharepoint(
    src: str | Path = "archives",
    dest: str | Path | None = None,
    *,
    client: Optional[SharePointClient] = None,
) -> int:
    """Upload files from ``src`` to SharePoint or copy to ``dest``.

    Parameters
    ----------
    src:
        Source directory containing archived files.
    dest:
        Destination directory when using local copy. When ``client`` is
        provided this is interpreted as the remote folder path and may be
        ``None`` for the drive root.
    client:
        When provided, files are uploaded via the Microsoft Graph API instead
        of copied locally.

    Returns
    -------
    int
        Number of files copied.

    Raises
    ------
    FileNotFoundError
        If ``src`` does not exist.
    ValueError
        If neither ``dest`` is provided nor ``SHAREPOINT_ROOT`` is set.
    """
    src_path = Path(src)
    if not src_path.is_dir():
        raise FileNotFoundError(f"{src_path} does not exist or is not a directory")

    if client is not None:
        folder = str(dest or "").strip("/")
        count = 0
        for item in src_path.rglob("*"):
            if item.is_file():
                rel = item.relative_to(src_path)
                key = f"{folder}/{rel}" if folder else str(rel)
                client.upload_file(key.replace("\\", "/"), item.read_bytes())
                count += 1
        return count

    if dest is None:
        env_dest = os.getenv("SHAREPOINT_ROOT")
        if not env_dest:
            raise ValueError("Destination must be provided or SHAREPOINT_ROOT set")
        dest_path = Path(env_dest).expanduser()
    else:
        dest_path = Path(dest).expanduser()

    dest_path.mkdir(parents=True, exist_ok=True)

    count = 0
    for item in src_path.rglob("*"):
        if item.is_file():
            target = dest_path / item.relative_to(src_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
            count += 1
    return count

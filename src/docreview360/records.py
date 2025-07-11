"""Utilities for syncing archive files to a SharePoint records repository."""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def sync_to_sharepoint(src: str | Path = "archives", dest: str | Path | None = None) -> int:
    """Copy files from ``src`` to the SharePoint ``dest`` directory.

    Parameters
    ----------
    src:
        Source directory containing archived files.
    dest:
        Destination directory. If omitted, uses the ``SHAREPOINT_ROOT``
        environment variable.

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

    if dest is None:
        env_dest = os.getenv("SHAREPOINT_ROOT")
        if not env_dest:
            raise ValueError("Destination must be provided or SHAREPOINT_ROOT set")
        dest_path = Path(env_dest)
    else:
        dest_path = Path(dest)

    dest_path.mkdir(parents=True, exist_ok=True)

    count = 0
    for item in src_path.rglob("*"):
        if item.is_file():
            target = dest_path / item.relative_to(src_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
            count += 1
    return count

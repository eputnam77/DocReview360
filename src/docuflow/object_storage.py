"""Lightweight file-based object storage plug-in."""

from __future__ import annotations

from pathlib import Path


def upload_file(bucket: str | Path, key: str, data: bytes) -> Path:
    """Save ``data`` to ``bucket``/``key`` and return the file path.

    Parameters
    ----------
    bucket:
        Root directory used as the storage bucket.
    key:
        Relative file path under the bucket. Must not be absolute or empty.
    data:
        File contents to write.

    Returns
    -------
    Path
        Location of the written file.
    """

    if not key or key.startswith("/") or key.endswith("/"):
        raise ValueError("invalid key")

    dest = Path(bucket) / key
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return dest

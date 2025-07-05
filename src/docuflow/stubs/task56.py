"""MinIO/S3 object storage helper."""

from __future__ import annotations

from pathlib import Path

from ..object_storage import upload_file
from . import record_task_completion


def task56(bucket: str | Path, key: str, data: bytes) -> Path:
    """Store ``data`` in ``bucket`` under ``key`` and return the path."""
    record_task_completion(56)
    return upload_file(bucket, key, data)

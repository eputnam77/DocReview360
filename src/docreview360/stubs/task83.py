"""MinIO/S3 object storage plugin stub."""

from __future__ import annotations

import uuid
from typing import Dict

from . import record_task_completion

_STORAGE: Dict[str, bytes] = {}


def upload_binary(data: bytes) -> str:
    """Store ``data`` and return a pseudo presigned URL."""
    if not data:
        raise ValueError("data required")
    key = uuid.uuid4().hex
    _STORAGE[key] = data
    record_task_completion(83)
    return f"https://s3.example/{key}?signature=dummy"


def download_binary(url: str) -> bytes:
    """Return the binary content referenced by ``url``."""
    key = url.split("/")[-1].split("?")[0]
    if key not in _STORAGE:
        raise KeyError(key)
    record_task_completion(83)
    return _STORAGE[key]

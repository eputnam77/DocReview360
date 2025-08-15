"""Hash chaining utilities for audit logs.

This module batches audit log entries, computes a SHA-256 hash chain and
persists the resulting chain to an append-only storage location. A companion
verification helper recomputes the chain from the current audit log table and
compares it against the stored chain to detect tampering.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable, List

from .logs import export_logs
from .object_storage import download_file, upload_file


def _serialize_batch(batch: Iterable) -> bytes:
    """Return a stable JSON representation of ``batch``."""

    return json.dumps([e.model_dump() for e in batch], sort_keys=True, default=str).encode()


def _compute_chain(batches: Iterable[Iterable]) -> List[str]:
    """Compute a SHA-256 hash chain for the given batches."""

    chain: List[str] = []
    prev = b""
    for batch in batches:
        data = _serialize_batch(batch)
        digest = hashlib.sha256(prev + data).hexdigest()
        chain.append(digest)
        prev = bytes.fromhex(digest)
    return chain


def batch_hash_logs(
    *,
    batch_size: int = 100,
    bucket: str | Path = "tamper_proof_store",
    key: str = "log_chain.json",
) -> List[str]:
    """Hash log entries in batches and store the chain in ``bucket``.

    Parameters
    ----------
    batch_size:
        Number of log entries per batch.
    bucket:
        Destination directory or S3 bucket used as the append-only store.
    key:
        File name for the stored chain within ``bucket``.
    """

    entries = export_logs()
    batches = [entries[i : i + batch_size] for i in range(0, len(entries), batch_size)]
    chain = _compute_chain(batches)
    upload_file(bucket, key, json.dumps(chain).encode(), append_only=True)
    return chain


def verify_hash_chain(
    *,
    batch_size: int = 100,
    bucket: str | Path = "tamper_proof_store",
    key: str = "log_chain.json",
) -> bool:
    """Verify the stored hash chain matches current log entries.

    Returns ``True`` when the recomputed chain equals the persisted one and
    ``False`` otherwise. Missing chain files also yield ``False``.
    """

    try:
        stored = json.loads(download_file(bucket, key).decode())
    except Exception:
        return False
    entries = export_logs()
    batches = [entries[i : i + batch_size] for i in range(0, len(entries), batch_size)]
    current = _compute_chain(batches)
    return stored == current

"""Lightweight file-based object storage plug-in."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path


def download_file(bucket: str | Path, key: str) -> bytes:
    """Return the contents of ``bucket``/``key``.

    Parameters
    ----------
    bucket:
        Root directory used as the storage bucket.
    key:
        Relative file path under the bucket. Must not be absolute or empty.

    Returns
    -------
    bytes
        The file contents.
    """

    if not key or key.startswith("/") or key.endswith("/"):
        raise ValueError("invalid key")

    # Support reading from S3 when ``bucket`` is an ``s3://`` URL. The
    # dependency on :mod:`boto3` is optional so tests that only use the file
    # system do not require the package.
    if str(bucket).startswith("s3://"):
        import boto3  # type: ignore

        s3 = boto3.client("s3")
        bucket_name = str(bucket)[5:]
        obj = s3.get_object(Bucket=bucket_name, Key=key)
        return obj["Body"].read()

    path = Path(bucket) / key
    return path.read_bytes()


def upload_file(
    bucket: str | Path,
    key: str,
    data: bytes,
    *,
    append_only: bool = False,
    retention_days: int = 1,
) -> Path | str:
    """Save ``data`` to ``bucket``/``key`` and return the file path.

    Parameters
    ----------
    bucket:
        Root directory used as the storage bucket.
    key:
        Relative file path under the bucket. Must not be absolute or empty.
    data:
        File contents to write.
    append_only:
        When ``True`` existing objects will not be overwritten. For S3
        destinations an object lock in ``COMPLIANCE`` mode is applied so the
        object becomes append-only.
    retention_days:
        Optional retention period for S3 object lock.

    Returns
    -------
    Path | str
        Location of the written file or S3 URI.
    """

    if not key or key.startswith("/") or key.endswith("/"):
        raise ValueError("invalid key")

    # Handle S3 buckets via ``boto3`` if the bucket name is an ``s3://`` URL.
    if str(bucket).startswith("s3://"):
        import boto3  # type: ignore

        s3 = boto3.client("s3")
        bucket_name = str(bucket)[5:]
        extra: dict[str, object] = {}
        if append_only:
            retain_until = datetime.now(timezone.utc) + timedelta(days=retention_days)
            extra = {
                "ObjectLockMode": "COMPLIANCE",
                "ObjectLockRetainUntilDate": retain_until,
            }
        s3.put_object(Bucket=bucket_name, Key=key, Body=data, **extra)
        return f"s3://{bucket_name}/{key}"

    dest = Path(bucket) / key
    dest.parent.mkdir(parents=True, exist_ok=True)
    if append_only and dest.exists():
        raise FileExistsError("object already exists")
    dest.write_bytes(data)
    return dest
